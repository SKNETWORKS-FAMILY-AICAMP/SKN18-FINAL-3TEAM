# Lambda → GitHub Actions 배포 자동화

Lambda 함수를 호출하면 GitHub Actions 워크플로우가 트리거되어 ECS 서비스를 자동으로 배포합니다.

## 📋 사전 준비

### 1. GitHub Personal Access Token 생성

1. GitHub 계정 → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)" 클릭
3. 권한 선택:
   - ✅ `repo` (전체)
   - ✅ `workflow`
4. 토큰 생성 후 복사 (한 번만 표시됨!)

### 2. GitHub Repository Secrets 설정

`.github/workflows/deploy-ecs.yml` 워크플로우에서 사용할 AWS 자격증명을 GitHub Secrets에 등록:

1. GitHub Repository → Settings → Secrets and variables → Actions
2. "New repository secret" 클릭
3. 다음 시크릿 등록:
   - `AWS_ACCESS_KEY_ID`: AWS Access Key
   - `AWS_SECRET_ACCESS_KEY`: AWS Secret Key

## 🚀 배포 순서

### 1단계: Lambda 함수 배포

```bash
aws cloudformation deploy \
  --stack-name skn18-3-lambda-trigger \
  --template-file cloudformation/cicd/lambda-trigger-github-actions.yaml \
  --region ap-northeast-2 \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    NamePrefix=skn18-3-dev \
    GitHubRepo="your-username/SKN18-FINAL-3TEAM" \
    GitHubToken="ghp_your_github_token_here"
```

**파라미터 설명:**
- `GitHubRepo`: GitHub 리포지토리 (형식: `owner/repo`)
- `GitHubToken`: 위에서 생성한 GitHub Personal Access Token

### 2단계: GitHub Actions 워크플로우 확인

`.github/workflows/deploy-ecs.yml` 파일이 리포지토리에 커밋되어 있는지 확인:

```bash
git add .github/workflows/deploy-ecs.yml
git commit -m "feat: Add ECS deployment workflow"
git push origin main
```

## 📞 Lambda 함수 호출 방법

### 방법 1: AWS CLI로 직접 호출

```bash
# Web 서비스만 배포
aws lambda invoke \
  --function-name skn18-3-dev-github-trigger \
  --payload '{"service": "web"}' \
  --region ap-northeast-2 \
  response.json

# Celery 서비스만 배포
aws lambda invoke \
  --function-name skn18-3-dev-github-trigger \
  --payload '{"service": "celery"}' \
  --region ap-northeast-2 \
  response.json

# 모든 서비스 배포
aws lambda invoke \
  --function-name skn18-3-dev-github-trigger \
  --payload '{"service": "all"}' \
  --region ap-northeast-2 \
  response.json

# 응답 확인
cat response.json
```

### 방법 2: Python/Boto3로 호출

```python
import boto3
import json

lambda_client = boto3.client('lambda', region_name='ap-northeast-2')

response = lambda_client.invoke(
    FunctionName='skn18-3-dev-github-trigger',
    InvocationType='RequestResponse',
    Payload=json.dumps({'service': 'web'})
)

result = json.loads(response['Payload'].read())
print(result)
```

### 방법 3: API Gateway 연결 (선택사항)

API Gateway를 추가로 설정하면 HTTP 엔드포인트로 호출 가능합니다.

## 🔄 배포 프로세스

Lambda 함수를 호출하면 다음과 같은 과정이 진행됩니다:

```
1. Lambda 함수 호출
   ↓
2. GitHub Actions API 호출 (workflow dispatch)
   ↓
3. GitHub Actions 워크플로우 시작
   ↓
4. Docker 이미지 빌드 (backend/Dockerfile)
   ↓
5. ECR에 이미지 푸시
   ↓
6. ECS 서비스 강제 재배포 (forceNewDeployment)
   ↓
7. ECS가 새 태스크 시작 및 이전 태스크 종료
   ↓
8. 배포 완료
```

## ⏱️ 예상 소요 시간

- **Web 서비스**: 약 5-10분
  - Docker 빌드: 3-5분
  - ECR 푸시: 1-2분
  - ECS 배포: 2-3분

- **Celery 서비스**: 약 5-10분
  - Docker 빌드: 3-5분 (Web과 동일한 이미지)
  - ECR 푸시: 1-2분
  - ECS 배포: 2-3분

- **All (Web + Celery)**: 약 5-10분
  - 두 서비스가 병렬로 배포됨

## 📊 배포 상태 모니터링

### GitHub Actions에서 확인

1. GitHub Repository → Actions 탭
2. "Deploy to ECS" 워크플로우 클릭
3. 실시간 로그 확인

### AWS 콘솔에서 확인

```bash
# ECS 서비스 상태 확인
aws ecs describe-services \
  --cluster skn18-3-dev-cluster \
  --services skn18-3-dev-web skn18-3-dev-celery \
  --region ap-northeast-2

# 실행 중인 태스크 확인
aws ecs list-tasks \
  --cluster skn18-3-dev-cluster \
  --service-name skn18-3-dev-web \
  --region ap-northeast-2

# Lambda 로그 확인
aws logs tail /aws/lambda/skn18-3-dev-github-trigger \
  --follow \
  --region ap-northeast-2
```

## ❌ 문제 해결

### Lambda 함수 호출 실패

```bash
# Lambda 로그 확인
aws logs tail /aws/lambda/skn18-3-dev-github-trigger \
  --follow \
  --region ap-northeast-2
```

**일반적인 원인:**
- GitHub Token 만료 또는 권한 부족
- GitHub Repository 이름 오류
- 네트워크 연결 문제

### GitHub Actions 워크플로우가 트리거되지 않음

**확인 사항:**
1. GitHub Token에 `repo`, `workflow` 권한이 있는지 확인
2. `.github/workflows/deploy-ecs.yml` 파일이 main 브랜치에 있는지 확인
3. GitHub Repository 이름이 정확한지 확인 (대소문자 구분)

### Docker 빌드 실패

GitHub Actions 로그에서 빌드 에러 확인:
```bash
# 로컬에서 Docker 빌드 테스트
docker build -t test-web:latest -f backend/Dockerfile .
```

### ECS 배포 실패

```bash
# ECS 서비스 이벤트 확인
aws ecs describe-services \
  --cluster skn18-3-dev-cluster \
  --services skn18-3-dev-web \
  --region ap-northeast-2 \
  --query 'services[0].events[:5]'

# ECS 태스크 로그 확인
aws logs tail /ecs/skn18-3-dev-web \
  --follow \
  --region ap-northeast-2
```

## 🔐 보안 고려사항

1. **GitHub Token 관리**
   - Token을 CloudFormation 파라미터로 직접 전달하지 말고 SSM Parameter Store 사용 권장
   - Token은 필요한 최소 권한만 부여

2. **AWS 자격증명**
   - GitHub Secrets는 암호화되어 저장됨
   - IAM 역할 사용 권장 (OIDC Provider 설정)

3. **Lambda 함수 접근 제어**
   - 필요시 API Gateway + API Key로 보호
   - VPC 내부에서만 호출하도록 제한 가능

## 📝 참고 자료

- [GitHub Actions - Manual triggers (workflow_dispatch)](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch)
- [AWS ECS - Updating a service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/update-service.html)
- [GitHub REST API - Create a workflow dispatch event](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)
