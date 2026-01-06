using UnityEngine;

namespace minji_run
{
    /// <summary>
    /// 오브젝트 Scale에 따라 Material Tiling을 자동 조정
    /// Scale을 늘려도 텍스처가 늘어나지 않고 반복됨
    /// </summary>
    [ExecuteInEditMode]
    public class AutoTiling : MonoBehaviour
    {
        [Header("Tiling Mode")]
        [Tooltip("어떤 모드로 Tiling을 적용할지 선택")]
        [SerializeField] private TilingMode mode = TilingMode.AutoDetect;

        public enum TilingMode
        {
            AutoDetect,     // 자동 감지 (제일 많이 늘어난 축 기준)
            ManualMapping   // 수동 설정 (아래 Multiplier 사용)
        }

        [Header("Manual Mapping (Manual Mode Only)")]
        [Tooltip("Scale X축이 Tiling (U, V)에 미치는 영향")]
        [SerializeField] private Vector2 scaleXMultiplier = new Vector2(1, 0);

        [Tooltip("Scale Y축이 Tiling (U, V)에 미치는 영향")]
        [SerializeField] private Vector2 scaleYMultiplier = new Vector2(0, 0);

        [Tooltip("Scale Z축이 Tiling (U, V)에 미치는 영향")]
        [SerializeField] private Vector2 scaleZMultiplier = new Vector2(0, 1);

        [Header("Base Settings")]
        [SerializeField] private Vector2 baseTiling = Vector2.one;
        [SerializeField] private Vector3 referenceScale = Vector3.one;

        private Renderer meshRenderer;
        private Material[] materials;
        private Vector3 lastScale;

        private void Start()
        {
            InitializeMaterials();
        }

        private void OnEnable()
        {
            if (materials == null || materials.Length == 0)
            {
                InitializeMaterials();
            }
        }

        private void InitializeMaterials()
        {
            meshRenderer = GetComponent<Renderer>();
            if (meshRenderer != null)
            {
                Material[] sharedMats = meshRenderer.sharedMaterials;

                // 에디터에서 재생 중이 아니면 Material 인스턴스를 만들지 않음 (프리팹 모드)
                #if UNITY_EDITOR
                if (!Application.isPlaying && UnityEditor.PrefabUtility.IsPartOfPrefabAsset(gameObject))
                {
                    // 프리팹 모드에서는 원본 Material 유지
                    materials = sharedMats;
                    return;
                }
                #endif

                materials = new Material[sharedMats.Length];

                if (baseTiling == Vector2.one && sharedMats.Length > 0 && sharedMats[0] != null)
                {
                    baseTiling = sharedMats[0].mainTextureScale;
                }

                for (int i = 0; i < sharedMats.Length; i++)
                {
                    if (sharedMats[i] != null)
                    {
                        // Material 인스턴스 생성 (원본 보호)
                        materials[i] = new Material(sharedMats[i]);
                        materials[i].name = sharedMats[i].name + " (AutoTiling Instance)";
                    }
                }

                meshRenderer.materials = materials;

                if (referenceScale == Vector3.one)
                {
                    referenceScale = transform.localScale;
                }
                lastScale = referenceScale;

                UpdateTiling();
            }
        }

        private void Update()
        {
            if (transform.localScale != lastScale)
            {
                UpdateTiling();
                lastScale = transform.localScale;
            }
        }

        private void UpdateTiling()
        {
            if (materials == null || materials.Length == 0) return;

            float ratioX = transform.localScale.x / referenceScale.x;
            float ratioY = transform.localScale.y / referenceScale.y;
            float ratioZ = transform.localScale.z / referenceScale.z;

            Vector2 newTiling = baseTiling;

            if (mode == TilingMode.AutoDetect)
            {
                // 자동 모드: X, Y, Z 중 가장 많이 변한 축을 U와 V에 각각 적용
                // 일반적으로 X → U (가로), Z → V (세로)로 매핑
                newTiling.x = baseTiling.x * ratioX;
                newTiling.y = baseTiling.y * ratioZ;
            }
            else
            {
                // 수동 모드: 사용자 지정 Multiplier 사용
                newTiling.x = baseTiling.x * (
                    (scaleXMultiplier.x * ratioX) +
                    (scaleYMultiplier.x * ratioY) +
                    (scaleZMultiplier.x * ratioZ)
                );

                newTiling.y = baseTiling.y * (
                    (scaleXMultiplier.y * ratioX) +
                    (scaleYMultiplier.y * ratioY) +
                    (scaleZMultiplier.y * ratioZ)
                );
            }

            newTiling.x = Mathf.Max(0.01f, newTiling.x);
            newTiling.y = Mathf.Max(0.01f, newTiling.y);

            foreach (Material mat in materials)
            {
                if (mat != null)
                {
                    mat.mainTextureScale = newTiling;
                }
            }
        }

        [ContextMenu("Reset Reference Scale")]
        public void ResetReferenceScale()
        {
            referenceScale = transform.localScale;
            UpdateTiling();
        }

        [ContextMenu("Preset: Floor/Ceiling (X=Width, Z=Depth)")]
        public void PresetFloor()
        {
            mode = TilingMode.ManualMapping;
            scaleXMultiplier = new Vector2(1, 0);
            scaleYMultiplier = new Vector2(0, 0);
            scaleZMultiplier = new Vector2(0, 1);
            UpdateTiling();
        }

        [ContextMenu("Preset: Wall (X=Width, Y=Height)")]
        public void PresetWall()
        {
            mode = TilingMode.ManualMapping;
            scaleXMultiplier = new Vector2(1, 0);
            scaleYMultiplier = new Vector2(0, 1);
            scaleZMultiplier = new Vector2(0, 0);
            UpdateTiling();
        }

        [ContextMenu("Preset: Long Wall (Z=Length, Y=Height)")]
        public void PresetLongWall()
        {
            mode = TilingMode.ManualMapping;
            scaleXMultiplier = new Vector2(0, 0);
            scaleYMultiplier = new Vector2(0, 1);
            scaleZMultiplier = new Vector2(1, 0);
            UpdateTiling();
        }

        #if UNITY_EDITOR
        /// <summary>
        /// 현재 적용된 Tiling 값으로 Material을 Asset으로 저장하고 오브젝트에 적용
        /// 프리팹 제작 전에 사용
        /// </summary>
        [ContextMenu("Bake Material (Save Tiling as Asset)")]
        public void BakeMaterial()
        {
            if (materials == null || materials.Length == 0)
            {
                Debug.LogWarning("[AutoTiling] No materials to bake!");
                return;
            }

            string folderPath = "Assets/Materials/AutoTiled";

            // 폴더가 없으면 생성
            if (!UnityEditor.AssetDatabase.IsValidFolder(folderPath))
            {
                if (!UnityEditor.AssetDatabase.IsValidFolder("Assets/Materials"))
                {
                    UnityEditor.AssetDatabase.CreateFolder("Assets", "Materials");
                }
                UnityEditor.AssetDatabase.CreateFolder("Assets/Materials", "AutoTiled");
            }

            Material[] bakedMaterials = new Material[materials.Length];

            for (int i = 0; i < materials.Length; i++)
            {
                if (materials[i] != null)
                {
                    // 새 Material 생성 (현재 Tiling 값 복사)
                    Material bakedMat = new Material(materials[i]);
                    bakedMat.name = $"{gameObject.name}_Baked_{i}";

                    // Asset으로 저장
                    string assetPath = $"{folderPath}/{bakedMat.name}.mat";
                    assetPath = UnityEditor.AssetDatabase.GenerateUniqueAssetPath(assetPath);

                    UnityEditor.AssetDatabase.CreateAsset(bakedMat, assetPath);
                    bakedMaterials[i] = bakedMat;

                    Debug.Log($"[AutoTiling] Baked material saved: {assetPath} (Tiling: {bakedMat.mainTextureScale})");
                }
            }

            // 저장된 Material을 오브젝트에 적용
            if (meshRenderer != null)
            {
                meshRenderer.sharedMaterials = bakedMaterials;
            }

            UnityEditor.AssetDatabase.SaveAssets();
            UnityEditor.AssetDatabase.Refresh();

            Debug.Log($"[AutoTiling] ✓ Baked {bakedMaterials.Length} material(s). You can now remove AutoTiling component and create prefab.");
        }
        #endif
    }
}
