#!/bin/bash
# .restack 파일을 여러 개로 나누어 병렬로 실행하는 스크립트

# 프로젝트 루트로 이동
cd "$(dirname "$0")/../../../.."

# 설정
RESTACK_FILE="backend/ontology_langgraph_structure/ontology/instances/.restack"
LOG_DIR="backend/ontology_langgraph_structure/ontology/logs"
INSTANCES_DIR="backend/ontology_langgraph_structure/ontology/instances"
PARALLEL_COUNT=4  # 병렬 실행할 프로세스 수

mkdir -p "$LOG_DIR"

echo "=========================================="
echo "🚀 .restack 병렬 처리 스크립트"
echo "=========================================="
echo ""

# .restack 파일 확인
if [ ! -f "$RESTACK_FILE" ]; then
    echo "❌ .restack 파일이 없습니다: $RESTACK_FILE"
    exit 1
fi

# .restack 파일 내용 확인
RESTACK_COUNT=$(grep -v '^$' "$RESTACK_FILE" | grep -c '^[0-9]')
if [ "$RESTACK_COUNT" -eq 0 ]; then
    echo "⚠️  .restack 파일에 처리할 행이 없습니다."
    exit 1
fi

echo "📋 원본 .restack 파일: $RESTACK_FILE"
echo "📋 총 행 수: $RESTACK_COUNT개"
echo "🔢 병렬 프로세스 수: $PARALLEL_COUNT개"
echo ""

# 이미 분할된 .restack 파일 확인 또는 새로 분할
PIDS=()
LOG_FILES=()
RESTACK_FILES=()

echo "📝 분할된 .restack 파일 확인 중..."
ALL_PARTS_EXIST=true
for i in $(seq 1 $PARALLEL_COUNT); do
    RESTACK_PART="${INSTANCES_DIR}/.restack_part${i}"
    if [ ! -f "$RESTACK_PART" ]; then
        ALL_PARTS_EXIST=false
        break
    fi
done

if [ "$ALL_PARTS_EXIST" = false ]; then
    echo "  ⚠️  분할된 파일이 없습니다. 새로 분할합니다..."
    RESTACK_ROWS=($(grep -v '^$' "$RESTACK_FILE" | grep '^[0-9]' | sort -n))
    TOTAL_ROWS=${#RESTACK_ROWS[@]}
    ROWS_PER_PROCESS=$(( ($TOTAL_ROWS + $PARALLEL_COUNT - 1) / $PARALLEL_COUNT ))  # 올림 계산
    
    for i in $(seq 1 $PARALLEL_COUNT); do
        START_IDX=$(( ($i - 1) * $ROWS_PER_PROCESS ))
        END_IDX=$(( $i * $ROWS_PER_PROCESS ))
        
        if [ $START_IDX -ge $TOTAL_ROWS ]; then
            echo "  ⚠️  프로세스 $i: 범위를 벗어남 (건너뜀)"
            continue
        fi
        
        # 각 프로세스용 .restack 파일 생성
        RESTACK_PART="${INSTANCES_DIR}/.restack_part${i}"
        
        # 해당 범위의 행 번호만 추출
        > "$RESTACK_PART"  # 파일 초기화
        for j in $(seq $START_IDX $((END_IDX - 1))); do
            if [ $j -lt $TOTAL_ROWS ]; then
                echo "${RESTACK_ROWS[$j]}" >> "$RESTACK_PART"
            fi
        done
        
        PART_COUNT=$(wc -l < "$RESTACK_PART" | tr -d ' ')
        echo "  ✅ 생성: $RESTACK_PART ($PART_COUNT개 행)"
    done
else
    echo "  ✅ 이미 분할된 파일이 있습니다."
fi

# 통합 로그 파일 (모든 프로세스 로그가 섞여서 저장)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
UNIFIED_LOG="${LOG_DIR}/restack_ttl_unified_${TIMESTAMP}.log"
> "$UNIFIED_LOG"  # 통합 로그 파일 초기화

# 각 프로세스 실행
for i in $(seq 1 $PARALLEL_COUNT); do
    RESTACK_PART="${INSTANCES_DIR}/.restack_part${i}"
    LOG_FILE="${LOG_DIR}/restack_ttl_part${i}_${TIMESTAMP}.log"
    
    if [ ! -f "$RESTACK_PART" ]; then
        echo "  ⚠️  프로세스 $i: $RESTACK_PART 파일이 없습니다 (건너뜀)"
        continue
    fi
    
    PART_COUNT=$(wc -l < "$RESTACK_PART" | tr -d ' ')
    echo "  ✅ 프로세스 $i: $RESTACK_PART ($PART_COUNT개 행)"
    
    RESTACK_FILES+=("$RESTACK_PART")
    LOG_FILES+=("$LOG_FILE")
    
    # 각 프로세스 실행 (백그라운드로 자동 실행)
    # 로그를 개별 파일과 통합 로그에 동시에 기록 (프로세스 번호 표시)
    # PYTHONUNBUFFERED=1로 버퍼링 비활성화, stdbuf로 추가 버퍼링 제거
    nohup bash -c "export PYTHONUNBUFFERED=1 && source .venv/bin/activate && stdbuf -oL -eL caffeinate -i python -u backend/ontology_langgraph_structure/ontology/scripts/generate_restack_ttl.py --restack-file '$RESTACK_PART' --part-number $i 2>&1 | stdbuf -oL sed \"s/^/[Part$i] /\" | tee -a '$LOG_FILE' >> '$UNIFIED_LOG'" &
    
    PID=$!
    PIDS+=($PID)
    echo "    🔢 PID: $PID"
    echo "    📄 개별 로그: $LOG_FILE"
done

echo ""
echo "================================"
echo "병렬 실행 시작!"
echo "================================"
echo ""
echo "📌 실행 중인 프로세스:"
for i in $(seq 1 ${#PIDS[@]}); do
    PID=${PIDS[$((i-1))]}
    LOG_FILE=${LOG_FILES[$((i-1))]}
    RESTACK_PART=${RESTACK_FILES[$((i-1))]}
    echo "  프로세스 $i:"
    echo "    PID: $PID"
    echo "    .restack: $RESTACK_PART"
    echo "    로그: $LOG_FILE"
    echo "    확인: tail -f $LOG_FILE"
    echo "    종료: kill $PID"
    echo ""
done

# PID 파일 저장
echo "${PIDS[@]}" > "$LOG_DIR/restack_parallel_pids.txt"

echo "💡 로그 확인 방법:"
echo "   - 통합 로그 (모든 프로세스 로그가 섞여서): tail -f $UNIFIED_LOG"
echo "   - 개별 로그 (각 프로세스별): tail -f ${LOG_DIR}/restack_ttl_part*_${TIMESTAMP}.log"
echo ""
echo "💡 모든 프로세스 종료하려면:"
echo "   kill \$(cat $LOG_DIR/restack_parallel_pids.txt)"
echo ""
echo "💡 완료 후 결과 파일 합치기:"
echo "   cat ${INSTANCES_DIR}/korean_history_instances_2_part*.ttl > ${INSTANCES_DIR}/korean_history_instances_2_merged.ttl"
echo ""

