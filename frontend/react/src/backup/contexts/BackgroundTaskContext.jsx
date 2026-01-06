import { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import Toast from '../components/common/Toast/Toast';
import { checkTaskStatus } from '../api/communityApi';

const BackgroundTaskContext = createContext();

export const useBackgroundTask = () => {
  const context = useContext(BackgroundTaskContext);
  if (!context) {
    throw new Error('useBackgroundTask must be used within BackgroundTaskProvider');
  }
  return context;
};

export const BackgroundTaskProvider = ({ children }) => {
  const [tasks, setTasks] = useState(new Map());
  const [toasts, setToasts] = useState([]);
  const taskIdCounter = useRef(0);

  // 토스트 추가
  const showToast = useCallback((message, type = 'success') => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, type }]);
  }, []);

  // 토스트 제거
  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  // 백그라운드 작업 등록
  const registerTask = useCallback((taskName, promise) => {
    const taskId = ++taskIdCounter.current;

    setTasks((prev) => {
      const newTasks = new Map(prev);
      newTasks.set(taskId, {
        id: taskId,
        name: taskName,
        status: 'running',
        createdAt: Date.now(),
      });
      return newTasks;
    });

    // Promise 처리
    promise
      .then((result) => {
        setTasks((prev) => {
          const newTasks = new Map(prev);
          newTasks.set(taskId, {
            ...newTasks.get(taskId),
            status: 'completed',
            result,
            completedAt: Date.now(),
          });
          return newTasks;
        });

        // 성공 토스트 표시
        showToast(`${taskName} 완료`, 'success');

        // 완료된 작업 5초 후 제거
        setTimeout(() => {
          setTasks((prev) => {
            const newTasks = new Map(prev);
            newTasks.delete(taskId);
            return newTasks;
          });
        }, 5000);
      })
      .catch((error) => {
        setTasks((prev) => {
          const newTasks = new Map(prev);
          newTasks.set(taskId, {
            ...newTasks.get(taskId),
            status: 'failed',
            error: error.message || '작업 실패',
            completedAt: Date.now(),
          });
          return newTasks;
        });

        // 실패 토스트 표시
        showToast(`${taskName} 실패: ${error.message || '오류 발생'}`, 'error');

        // 실패한 작업 5초 후 제거
        setTimeout(() => {
          setTasks((prev) => {
            const newTasks = new Map(prev);
            newTasks.delete(taskId);
            return newTasks;
          });
        }, 5000);
      });

    return taskId;
  }, [showToast]);

  // 작업 취소
  const cancelTask = useCallback((taskId) => {
    setTasks((prev) => {
      const newTasks = new Map(prev);
      const task = newTasks.get(taskId);
      if (task) {
        newTasks.set(taskId, {
          ...task,
          status: 'cancelled',
          completedAt: Date.now(),
        });
      }
      return newTasks;
    });

    // 취소된 작업 즉시 제거
    setTimeout(() => {
      setTasks((prev) => {
        const newTasks = new Map(prev);
        newTasks.delete(taskId);
        return newTasks;
      });
    }, 1000);
  }, []);

  // Celery task 폴링 시작
  const startCeleryTaskPolling = useCallback((celeryTaskId, taskName, onSuccess) => {
    const pollInterval = setInterval(async () => {
      try {
        const result = await checkTaskStatus(celeryTaskId);

        if (result.status === 'SUCCESS') {
          clearInterval(pollInterval);
          showToast(`${taskName} 완료`, 'success');
          if (onSuccess) onSuccess(result.result);
        } else if (result.status === 'FAILURE') {
          clearInterval(pollInterval);
          showToast(`${taskName} 실패: ${result.error || '오류 발생'}`, 'error');
        }
        // PENDING, STARTED 상태는 계속 폴링
      } catch (error) {
        console.error('Celery task 상태 확인 실패:', error);
        clearInterval(pollInterval);
        showToast(`${taskName} 상태 확인 실패`, 'error');
      }
    }, 3000); // 3초마다 폴링

    // 최대 5분 후 폴링 중단
    setTimeout(() => {
      clearInterval(pollInterval);
    }, 300000);

    return pollInterval;
  }, [showToast]);

  const value = {
    tasks: Array.from(tasks.values()),
    registerTask,
    cancelTask,
    showToast,
    startCeleryTaskPolling,
  };

  return (
    <BackgroundTaskContext.Provider value={value}>
      {children}

      {/* 토스트 컨테이너 */}
      <div style={{ position: 'fixed', top: 0, right: 0, zIndex: 10000 }}>
        {toasts.map((toast, index) => (
          <div
            key={toast.id}
            style={{
              marginTop: index === 0 ? '80px' : '8px',
            }}
          >
            <Toast
              message={toast.message}
              type={toast.type}
              onClose={() => removeToast(toast.id)}
            />
          </div>
        ))}
      </div>
    </BackgroundTaskContext.Provider>
  );
};
