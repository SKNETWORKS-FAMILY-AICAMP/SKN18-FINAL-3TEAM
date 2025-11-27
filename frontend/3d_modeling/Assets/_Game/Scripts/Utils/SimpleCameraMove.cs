using UnityEngine;

public class SimpleCameraMove : MonoBehaviour
{
    public float moveSpeed = 10f;
    public float rotateSpeed = 100f;

    void Update()
    {
        // 1. 이동 (WASD + QE 위아래)
        float h = Input.GetAxis("Horizontal"); // A, D
        float v = Input.GetAxis("Vertical");   // W, S
        float y = 0;
        
        if (Input.GetKey(KeyCode.E)) y = 1;    // 위
        if (Input.GetKey(KeyCode.Q)) y = -1;   // 아래

        Vector3 dir = new Vector3(h, y, v);
        transform.Translate(dir * moveSpeed * Time.deltaTime);

        // 2. 회전 (우클릭 누른 상태에서 마우스 이동)
        if (Input.GetMouseButton(1)) 
        {
            float mouseX = Input.GetAxis("Mouse X");
            float mouseY = Input.GetAxis("Mouse Y");

            transform.Rotate(Vector3.up * mouseX * rotateSpeed * Time.deltaTime, Space.World);
            transform.Rotate(Vector3.left * mouseY * rotateSpeed * Time.deltaTime, Space.Self);
        }
    }
}