using UnityEngine;

public class AutoFaceSync : StateMachineBehaviour
{
    // OnStateEnter: 이 애니메이션(노드)이 시작되는 순간 딱 1번 호출됨
    override public void OnStateEnter(Animator animator, AnimatorStateInfo stateInfo, int layerIndex)
    {
        //talking status start
        animator.SetBool("isTalking", true);
    }

    override public void OnStateExit(Animator animator, AnimatorStateInfo stateInfo, int layerIndex)
    {
        //talking status end
        animator.SetBool("isTalking", false);
    }
}