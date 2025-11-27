using UnityEngine;

public class AutoSmileSync : StateMachineBehaviour
{
    // 인사 시작할 때 -> 웃어라
    override public void OnStateEnter(Animator animator, AnimatorStateInfo stateInfo, int layerIndex)
    {
        animator.SetBool("isSmiling", true);
    }

    // 인사 끝날 때 -> 정색해라(기본 표정)
    override public void OnStateExit(Animator animator, AnimatorStateInfo stateInfo, int layerIndex)
    {
        animator.SetBool("isSmiling", false);
    }
}