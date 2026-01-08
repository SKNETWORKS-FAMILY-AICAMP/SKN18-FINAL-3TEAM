using UnityEngine;

/// <summary>
/// 바닥에서 위로 솟아오르는 벽 장애물 컨트롤러
/// 플레이어가 가까이 오면 빠르게 올라와 길을 막고, 일정 시간 후 다시 내려감
/// </summary>
public class PopupWallController : MonoBehaviour
{
    [Header("Popup Settings")]
    [SerializeField] private float riseHeight = 4f;        // 올라갈 높이
    [SerializeField] private float riseSpeed = 8f;         // 올라가는 속도
    [SerializeField] private float stayDuration = 2f;      // 위에서 머무는 시간
    [SerializeField] private float fallSpeed = 4f;         // 내려가는 속도
    [SerializeField] private float triggerDistance = 10f;  // 플레이어 감지 거리

    [Header("References")]
    [SerializeField] private Transform playerTransform;

    [Header("Debug")]
    [SerializeField] private bool showDebugMessages = false;

    private Vector3 hiddenPosition;   // 숨겨진 위치 (아래)
    private Vector3 visiblePosition;  // 보이는 위치 (위)
    private float currentStayTime = 0f;
    
    private enum WallState { Hidden, Rising, Visible, Falling }
    private WallState currentState = WallState.Hidden;

    void Start()
    {
        // Player 자동 탐색
        if (playerTransform == null)
        {
            GameObject playerObj = GameObject.FindGameObjectWithTag("Player");
            if (playerObj != null)
            {
                playerTransform = playerObj.transform;
                if (showDebugMessages)
                    Debug.Log($"[PopupWall] Player found: {playerObj.name}");
            }
            else
            {
                Debug.LogWarning("[PopupWall] Player not found! Make sure Player has 'Player' tag.");
            }
        }

        // 시작 위치 저장
        hiddenPosition = transform.position;
        visiblePosition = hiddenPosition + Vector3.up * riseHeight;

        if (showDebugMessages)
            Debug.Log($"[PopupWall] Initialized. Hidden: {hiddenPosition}, Visible: {visiblePosition}");
    }

    void Update()
    {
        if (playerTransform == null) return;

        float distanceToPlayer = Vector3.Distance(transform.position, playerTransform.position);

        switch (currentState)
        {
            case WallState.Hidden:
                // 플레이어가 가까우면 솟아오름
                if (distanceToPlayer < triggerDistance)
                {
                    currentState = WallState.Rising;
                    if (showDebugMessages)
                        Debug.Log($"[PopupWall] Rising! Distance: {distanceToPlayer:F1}m");
                }
                break;

            case WallState.Rising:
                // 위로 이동
                transform.position = Vector3.MoveTowards(transform.position, visiblePosition, riseSpeed * Time.deltaTime);
                if (Vector3.Distance(transform.position, visiblePosition) < 0.1f)
                {
                    currentState = WallState.Visible;
                    currentStayTime = 0f;
                    if (showDebugMessages)
                        Debug.Log("[PopupWall] Fully risen, staying up");
                }
                break;

            case WallState.Visible:
                // 위에서 대기
                currentStayTime += Time.deltaTime;
                if (currentStayTime >= stayDuration)
                {
                    currentState = WallState.Falling;
                    if (showDebugMessages)
                        Debug.Log("[PopupWall] Falling down");
                }
                break;

            case WallState.Falling:
                // 아래로 이동
                transform.position = Vector3.MoveTowards(transform.position, hiddenPosition, fallSpeed * Time.deltaTime);
                if (Vector3.Distance(transform.position, hiddenPosition) < 0.1f)
                {
                    currentState = WallState.Hidden;
                    if (showDebugMessages)
                        Debug.Log("[PopupWall] Hidden again");
                }
                break;
        }
    }

    // Scene 뷰에서 감지 거리 시각화
    void OnDrawGizmosSelected()
    {
        Gizmos.color = Color.yellow;
        Gizmos.DrawWireSphere(transform.position, triggerDistance);

        // 올라갈 위치 표시
        if (Application.isPlaying)
        {
            Gizmos.color = Color.green;
            Gizmos.DrawWireCube(visiblePosition, transform.localScale);
        }
        else
        {
            // 에디터 모드에서는 계산
            Vector3 previewVisible = transform.position + Vector3.up * riseHeight;
            Gizmos.color = Color.green;
            Gizmos.DrawWireCube(previewVisible, transform.localScale);
        }
    }

    /// <summary>
    /// 벽을 강제로 리셋 (Hidden 상태로)
    /// </summary>
    public void ResetWall()
    {
        transform.position = hiddenPosition;
        currentState = WallState.Hidden;
        currentStayTime = 0f;
        if (showDebugMessages)
            Debug.Log("[PopupWall] Reset to hidden position");
    }

    /// <summary>
    /// 벽을 강제로 올림
    /// </summary>
    public void ForceRise()
    {
        currentState = WallState.Rising;
    }

    // 프로퍼티로 현재 상태 확인 가능
    public bool IsVisible => currentState == WallState.Visible || currentState == WallState.Rising;
}
