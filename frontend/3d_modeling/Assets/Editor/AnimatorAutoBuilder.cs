using UnityEngine;
using UnityEditor;
using UnityEditor.Animations;
using System.IO; // 경로 제어를 위해 추가

public class AnimatorAutoBuilder : EditorWindow
{
    public AnimatorController targetController;
    public DefaultAsset motionFolder; // 애니메이션 클립이 있는 폴더
    public DefaultAsset dataFolder;   // [추가] 생성된 ActionTagData를 저장할 폴더
    public int targetLayerIndex = 0;

    [MenuItem("Tools/Auto Build Animator ⚡")]
    public static void ShowWindow()
    {
        GetWindow<AnimatorAutoBuilder>("Animator Builder");
    }

    void OnGUI()
    {
        GUILayout.Label("애니메이터 & 데이터 자동 생성기 v3.0", EditorStyles.boldLabel);

        targetController = (AnimatorController)EditorGUILayout.ObjectField("대상 애니메이터", targetController, typeof(AnimatorController), false);
        motionFolder = (DefaultAsset)EditorGUILayout.ObjectField("모션 폴더 (소스)", motionFolder, typeof(DefaultAsset), false);
        dataFolder = (DefaultAsset)EditorGUILayout.ObjectField("데이터 폴더 (저장소)", dataFolder, typeof(DefaultAsset), false); // [추가]

        targetLayerIndex = EditorGUILayout.IntField("타겟 레이어 번호 (0=Base)", targetLayerIndex);

        if (GUILayout.Button("자동 생성 시작! 🚀"))
        {
            if (targetController == null || motionFolder == null || dataFolder == null)
            {
                Debug.LogError("[에러] 애니메이터, 모션 폴더, 또는 데이터 폴더가 할당되지 않았습니다.");
                return;
            }
            // 레이어 범위 체크
            if (targetLayerIndex < 0 || targetLayerIndex >= targetController.layers.Length)
            {
                Debug.LogError($"[에러] 레이어 {targetLayerIndex}번은 존재하지 않습니다! (최대 {targetController.layers.Length - 1})");
                return;
            }
            BuildNodes();
        }
    }

    void BuildNodes()
    {
        string folderPath = AssetDatabase.GetAssetPath(motionFolder);
        string dataFolderPath = AssetDatabase.GetAssetPath(dataFolder); // [추가] 데이터 저장 경로

        Debug.Log($"[정보] 모션 검색 경로: {folderPath}");
        Debug.Log($"[정보] 데이터 저장 경로: {dataFolderPath}");

        string[] guids = AssetDatabase.FindAssets("t:AnimationClip", new[] { folderPath });

        if (guids.Length == 0)
        {
            Debug.LogWarning($"[경고] 해당 폴더에서 AnimationClip을 하나도 찾지 못했습니다.");
            return;
        }

        AnimatorStateMachine rootStateMachine = targetController.layers[targetLayerIndex].stateMachine;

        // Idle 찾기
        ChildAnimatorState idleStateObj = System.Array.Find(rootStateMachine.states, s => s.state.name == "Idle" || s.state.name == "Entry" || s.state.name == "Empty" || s.state.name == "None");
        AnimatorState destinationState = (idleStateObj.state != null) ? idleStateObj.state : rootStateMachine.defaultState;

        if (destinationState == null) Debug.LogWarning("[주의] 복귀할 Idle 상태를 찾지 못했습니다.");

        foreach (string guid in guids)
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            AnimationClip clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(path);

            if (clip == null) continue;

            string triggerName = clip.name;

            // ====================================================
            // [파트 1] Animator 설정 (기존 로직)
            // ====================================================

            // 1. 파라미터 추가
            bool paramExists = false;
            foreach (var p in targetController.parameters) { if (p.name == triggerName) paramExists = true; }
            if (!paramExists) targetController.AddParameter(triggerName, AnimatorControllerParameterType.Trigger);

            // 2. State 생성
            bool stateExists = false;
            foreach (var s in rootStateMachine.states)
            {
                if (s.state.name == clip.name)
                {
                    stateExists = true;
                    break;
                }
            }

            if (!stateExists)
            {
                AnimatorState newState = rootStateMachine.AddState(clip.name);
                newState.motion = clip;

                // Any State -> New State
                AnimatorStateTransition entryTrans = rootStateMachine.AddAnyStateTransition(newState);
                entryTrans.AddCondition(AnimatorConditionMode.If, 0, triggerName);
                entryTrans.duration = 0.1f;
                entryTrans.hasExitTime = false;
                entryTrans.canTransitionToSelf = false;

                // New State -> Idle
                if (destinationState != null)
                {
                    AnimatorStateTransition exitTrans = newState.AddTransition(destinationState);
                    exitTrans.hasExitTime = true;
                    exitTrans.exitTime = 1.0f;
                    exitTrans.duration = 0.25f;
                }
                Debug.Log($"<color=green>[애니메이터 생성]</color> {clip.name}");
            }
            else
            {
                Debug.LogWarning($"<color=yellow>[애니메이터 스킵]</color> {clip.name} (이미 존재)");
            }

            // ====================================================
            // [파트 2] Action Tag Data 생성 (신규 로직)
            // ====================================================
            
            // 파일 이름: "Tag_모션이름.asset"
            string assetName = $"Tag_{clip.name}.asset";
            string assetPath = $"{dataFolderPath}/{assetName}";

            // 이미 데이터 파일이 존재하는지 체크
            ActionTagData existingData = AssetDatabase.LoadAssetAtPath<ActionTagData>(assetPath);

            if (existingData == null)
            {
                ActionTagData newData = ScriptableObject.CreateInstance<ActionTagData>();
                
                // 1. Tag Name 설정 (소문자로 변환하여 LLM 친화적으로)
                newData.tagName = clip.name.ToLower();

                // 2. Type 및 세부 설정 (Face vs Body 구분)
                // 파일 이름에 "face" (대소문자 무관)가 포함되어 있는지 확인
                if (clip.name.ToLower().Contains("face"))
                {
                    newData.type = ActionType.Face;
                    // Face는 파라미터를 수동으로 넣어야 하므로 TriggerName이나 Params는 비워둡니다.
                }
                else
                {
                    newData.type = ActionType.Body;
                    // Body는 Trigger Name이 필수
                    newData.triggerName = clip.name; 
                }

                // 3. 파일 생성 및 저장
                AssetDatabase.CreateAsset(newData, assetPath);
                Debug.Log($"<color=cyan>[데이터 생성]</color> {assetName} ({newData.type})");
            }
            else
            {
                // 이미 있으면 굳이 덮어쓰지 않고 로그만 남김 (실수로 세팅한 값 날아가는 것 방지)
                Debug.Log($"[데이터 스킵] {assetName} (이미 존재)");
            }
        }
        
        // 변경 사항 저장
        AssetDatabase.SaveAssets();
        Debug.Log("🎉 모든 작업(애니메이터 + 데이터 파일) 완료!");
    }
}