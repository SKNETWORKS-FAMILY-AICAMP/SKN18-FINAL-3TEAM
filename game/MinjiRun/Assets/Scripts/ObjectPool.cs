using UnityEngine;
using System.Collections.Generic;

namespace minji_run
{
    /// <summary>
    /// 범용 오브젝트 풀 시스템
    /// WebGL 성능 최적화를 위한 재사용 가능한 오브젝트 관리
    /// </summary>
    public class ObjectPool : MonoBehaviour
    {
        [System.Serializable]
        public class Pool
        {
            public string tag;              // 풀 식별 태그
            public GameObject prefab;       // 오브젝트 프리팹
            public int size;                // 초기 풀 크기
        }

        public static ObjectPool Instance { get; private set; }

        [Header("Pools")]
        [SerializeField] private List<Pool> pools = new List<Pool>();
        [SerializeField] private Transform poolParent;  // 풀 오브젝트들의 부모

        private Dictionary<string, Queue<GameObject>> poolDictionary;

        private void Awake()
        {
            // 싱글톤 설정
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
        }

        private void Start()
        {
            // 풀 부모 오브젝트 생성
            if (poolParent == null)
            {
                GameObject parent = new GameObject("Object Pools");
                poolParent = parent.transform;
                poolParent.SetParent(transform);
            }

            // 풀 딕셔너리 초기화
            poolDictionary = new Dictionary<string, Queue<GameObject>>();

            // 각 풀 초기화
            foreach (Pool pool in pools)
            {
                Queue<GameObject> objectPool = new Queue<GameObject>();

                // 초기 오브젝트 생성
                for (int i = 0; i < pool.size; i++)
                {
                    GameObject obj = CreateNewObject(pool.prefab, pool.tag);
                    objectPool.Enqueue(obj);
                }

                poolDictionary.Add(pool.tag, objectPool);
            }
        }

        /// <summary>
        /// 새 오브젝트 생성
        /// </summary>
        private GameObject CreateNewObject(GameObject prefab, string tag)
        {
            GameObject obj = Instantiate(prefab);
            obj.name = $"{prefab.name} (Pooled)";
            obj.SetActive(false);

            // 풀 부모 아래에 배치
            obj.transform.SetParent(poolParent);

            return obj;
        }

        /// <summary>
        /// 풀에서 오브젝트 가져오기
        /// </summary>
        public GameObject SpawnFromPool(string tag, Vector3 position, Quaternion rotation)
        {
            if (!poolDictionary.ContainsKey(tag))
            {
                Debug.LogWarning($"[ObjectPool] Pool with tag '{tag}' doesn't exist!");
                return null;
            }

            GameObject objectToSpawn;

            // 풀에 사용 가능한 오브젝트가 있으면 가져오기
            if (poolDictionary[tag].Count > 0)
            {
                objectToSpawn = poolDictionary[tag].Dequeue();
            }
            else
            {
                // 풀이 비었으면 새로 생성
                Pool pool = pools.Find(p => p.tag == tag);
                if (pool != null)
                {
                    objectToSpawn = CreateNewObject(pool.prefab, tag);
                    Debug.LogWarning($"[ObjectPool] Pool '{tag}' exhausted, creating new object");
                }
                else
                {
                    Debug.LogError($"[ObjectPool] Cannot create new object for tag '{tag}'");
                    return null;
                }
            }

            // 오브젝트 활성화 및 위치 설정
            objectToSpawn.SetActive(true);
            objectToSpawn.transform.position = position;
            objectToSpawn.transform.rotation = rotation;

            // IPooledObject 인터페이스 구현 확인
            IPooledObject pooledObj = objectToSpawn.GetComponent<IPooledObject>();
            if (pooledObj != null)
            {
                pooledObj.OnObjectSpawn();
            }

            return objectToSpawn;
        }

        /// <summary>
        /// 오브젝트를 풀에 반환
        /// </summary>
        public void ReturnToPool(string tag, GameObject obj)
        {
            if (!poolDictionary.ContainsKey(tag))
            {
                Debug.LogWarning($"[ObjectPool] Pool with tag '{tag}' doesn't exist!");
                Destroy(obj);
                return;
            }

            // 오브젝트 비활성화
            obj.SetActive(false);
            obj.transform.SetParent(poolParent);

            // 풀에 반환
            poolDictionary[tag].Enqueue(obj);
        }

        /// <summary>
        /// 풀 추가 (런타임)
        /// </summary>
        public void AddPool(string tag, GameObject prefab, int size)
        {
            if (poolDictionary.ContainsKey(tag))
            {
                Debug.LogWarning($"[ObjectPool] Pool with tag '{tag}' already exists!");
                return;
            }

            Pool newPool = new Pool
            {
                tag = tag,
                prefab = prefab,
                size = size
            };

            pools.Add(newPool);

            Queue<GameObject> objectPool = new Queue<GameObject>();
            for (int i = 0; i < size; i++)
            {
                GameObject obj = CreateNewObject(prefab, tag);
                objectPool.Enqueue(obj);
            }

            poolDictionary.Add(tag, objectPool);

            Debug.Log($"[ObjectPool] Added new pool '{tag}' with size {size}");
        }

        /// <summary>
        /// 모든 풀 초기화
        /// </summary>
        public void ClearAllPools()
        {
            foreach (var pool in poolDictionary)
            {
                while (pool.Value.Count > 0)
                {
                    GameObject obj = pool.Value.Dequeue();
                    Destroy(obj);
                }
            }

            poolDictionary.Clear();
            pools.Clear();
        }
    }

    /// <summary>
    /// 풀된 오브젝트 인터페이스
    /// 오브젝트가 풀에서 스폰될 때 호출됨
    /// </summary>
    public interface IPooledObject
    {
        void OnObjectSpawn();
    }
}
