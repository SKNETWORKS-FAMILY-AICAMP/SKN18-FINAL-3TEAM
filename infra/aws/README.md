## aws 계정과 연결
```
aws sts get-caller-identity
```

## 📋 배포 순서 (전체 자동화)

모든 리소스를 CloudFormation으로 자동 관리합니다.

### 1단계: 네트워크 인프라 (필수)
```bash
aws cloudformation deploy \
  --stack-name skn18-3-network \
  --template-file cloudformation/network/network.yaml \
  --region ap-northeast-2 \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    NamePrefix=skn18-3-dev \
    EnableVpcEndpoints=true
```
**생성 리소스**: VPC, 서브넷 4개, IGW, NAT, ALB, 보안 그룹

---

### 2단계: S3 버킷 (필수)
```bash
aws cloudformation deploy \
  --stack-name skn18-3-storage \
  --template-file cloudformation/storage/s3-buckets.yaml \
  --region ap-northeast-2 \
  --parameter-overrides \
    NamePrefix=skn18-3-dev
```
**생성 리소스**: 6개 S3 버킷 (videos, final-videos, thumbnails, profiles, scripts, temp)

---

### 3단계: ECR 리포지토리 (필수)
```bash
aws cloudformation deploy \
  --stack-name skn18-3-ecr \
  --template-file cloudformation/ecs/ecr-repos.yaml \
  --region ap-northeast-2 \
  --parameter-overrides \
    NamePrefix=skn18-3-dev
```
**생성 리소스**: 5개 ECR 리포지토리 (web, postgres, neo4j, fuseki, redis)

---

### 4단계: 설정 파일 준비
```bash
# 1. ECS 파라미터 설정
cp cloudformation/ecs/ecs-params.txt.example cloudformation/ecs/ecs-params.txt
# 필요시 ecs-params.txt 편집 (메모리, CPU 등)

# 2. SSM 시크릿 설정
cp cloudformation/params/ssm-values.txt.example cloudformation/params/ssm-values.txt
# ssm-values.txt 편집하여 실제 API 키와 비밀번호 입력 (필수!)
```

---

### 5단계: SSM 파라미터 (필수)
```bash
# ssm-values.txt 파일을 읽어서 파라미터로 전달
aws cloudformation deploy \
  --stack-name skn18-3-params \
  --template-file cloudformation/params/ssm-params.yaml \
  --region ap-northeast-2 \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    NamePrefix=skn18-3-dev \
    DjangoSecretKey="your-secret-key" \
    PostgresPassword="your-password" \
    # ... (ssm-values.txt 참고)
```
**생성 리소스**: SSM Parameter Store 시크릿 값들

---

### 6단계: ECS Base 스택 (필수)
```bash
aws cloudformation deploy \
  --stack-name skn18-3-ecs \
  --template-file cloudformation/ecs/ecs-base.yaml \
  --region ap-northeast-2 \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    NamePrefix=skn18-3-dev
```
**생성 리소스**: ECS 클러스터, IAM 역할, CloudWatch 로그 그룹, Service Discovery

---

### 7단계: Docker 이미지 빌드 & ECR 푸시 (필수)
```bash
# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com

# Web 이미지 빌드 & 푸시
docker build -t skn18-3-dev-web:latest -f backend/Dockerfile .
docker tag skn18-3-dev-web:latest 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-web:latest
docker push 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-web:latest

# 공식 이미지 미러링
docker pull redis:7-alpine
docker tag redis:7-alpine 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-redis:latest
docker push 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-redis:latest

docker pull pgvector/pgvector:pg16
docker tag pgvector/pgvector:pg16 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-postgres:latest
docker push 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-postgres:latest

docker pull neo4j:5.18
docker tag neo4j:5.18 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-neo4j:latest
docker push 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-neo4j:latest

docker pull stain/jena-fuseki:latest
docker tag stain/jena-fuseki:latest 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-fuseki:latest
docker push 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-fuseki:latest
```

---

### 8단계: ECS EC2 스택 (필수)
```bash
aws cloudformation deploy \
  --stack-name skn18-3-ecs-ec2 \
  --template-file cloudformation/ecs/ecs-ec2.yaml \
  --region ap-northeast-2 \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    NamePrefix=skn18-3-dev \
    InstanceType=t3.2xlarge \
    WebMemory=4096 \
    CeleryMemory=8192
```
**생성 리소스**: EC2 인스턴스 2대, ECS 서비스 6개, Auto Scaling Group

---

### 9단계: Frontend (선택)
```bash
aws cloudformation deploy \
  --stack-name skn18-3-frontend \
  --template-file cloudformation/frontend/frontend-s3-cloudfront.yaml \
  --region ap-northeast-2 \
  --parameter-overrides \
    NamePrefix=skn18-3-dev
```
**생성 리소스**: S3 버킷 (frontend), CloudFront 배포

---

## ✅ 배포 완료 후 확인 사항

### Network 스택
```bash
aws cloudformation describe-stacks --stack-name skn18-3-network --region ap-northeast-2 --query "Stacks[0].Outputs"
```
- ALB DNS Name 확인
- VPC ID, Subnet IDs 확인

### ECS 스택
```bash
aws ecs list-services --cluster skn18-3-dev-cluster --region ap-northeast-2
aws ecs list-tasks --cluster skn18-3-dev-cluster --region ap-northeast-2
```
- 6개 서비스 ACTIVE 확인: web, celery, redis, postgres, neo4j, fuseki
- 모든 태스크 RUNNING 확인

### ALB 상태 확인
```bash
aws elbv2 describe-target-health \
  --target-group-arn $(aws cloudformation describe-stacks --stack-name skn18-3-network --query "Stacks[0].Outputs[?OutputKey=='AlbTargetGroupArn'].OutputValue" --output text --region ap-northeast-2) \
  --region ap-northeast-2
```
- Web 서비스 타겟이 healthy 상태인지 확인

-----------------------------------------

## Network 구축
### bash 명령어
```bash
aws cloudformation deploy \
  --stack-name skn18-3-network \
  --template-file network.yaml \
  --region ap-northeast-2 \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    NamePrefix=skn18-3-dev \
    EnableVpcEndpoints=true
```

### powershell 명령어
```powershell
aws cloudformation deploy `
  --stack-name skn18-3-network `
  --template-file network.yaml `
  --region ap-northeast-2 `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides `
    NamePrefix=skn18-3-dev `
    EnableVpcEndpoints=true
```
------------------------
## 배포 후 바로 확인할 것
### network 스택
- ALB → DNSName 출력\
  - EC2 콘솔 → Load Balancers → 대상 Application Load Balancer 선택
  - ALB Status : Active
  - Description 탭 : DNS name 필드 존재 여부
  ```
  예시:
  my-alb-123456.ap-northeast-2.elb.amazonaws.com
  ```

- VPC Endpoint들이 Available 상태
  - VPC 콘솔 → Endpoints
  - State : Available
  - Type: Interface Endpoint인지 Gateway Endpoint인지
  - Service name
  ```
  예시:
  com.amazonaws.ap-northeast-2.s3
  ```

- 서브넷 4개 + ALB 정상 생성
  - VPC 콘솔 → Subnets
  - 서브넷 개수 : 4개
  - 각 서브넷은 VPC ID 동일
  - Availability Zone 분산 여부
  ```
  예시:
  ap-northeast-2a, 2c
  ```

- ALB가 서브넷 4개에 정상 연결되었는지 확인
  - EC2 콘솔 → Load Balancers → ALB 선택 → Network mapping

------------------------
## 실패 시 확인할 것
```
aws cloudformation describe-stack-events --stack-name skn18-3-network --region ap-northeast-2
```


## Network 스택 내리기
### bash 명령어
```bash
aws cloudformation delete-stack \
  --stack-name skn18-3-network \
  --region ap-northeast-2
```

### powershell 명령어
```powershell
aws cloudformation delete-stack `
  --stack-name skn18-3-network `
  --region ap-northeast-2
```

-----------------------------------------

## S3 버킷 생성
### bash 명령어
```bash
aws cloudformation deploy \
  --stack-name skn18-3-storage \
  --template-file cloudformation/storage/s3-buckets.yaml \
  --region ap-northeast-2 \
  --parameter-overrides \
    NamePrefix=skn18-3-dev
```

### powershell 명령어
```powershell
aws cloudformation deploy `
  --stack-name skn18-3-storage `
  --template-file cloudformation/storage/s3-buckets.yaml `
  --region ap-northeast-2 `
  --parameter-overrides `
    NamePrefix=skn18-3-dev
```

-----------------------------------------

## ECR 리포지토리 생성
### bash 명령어
```bash
aws cloudformation deploy \
  --stack-name skn18-3-ecr \
  --template-file cloudformation/ecs/ecr-repos.yaml \
  --region ap-northeast-2 \
  --parameter-overrides \
    NamePrefix=skn18-3-dev
```

### powershell 명령어
```powershell
aws cloudformation deploy `
  --stack-name skn18-3-ecr `
  --template-file cloudformation/ecs/ecr-repos.yaml `
  --region ap-northeast-2 `
  --parameter-overrides `
    NamePrefix=skn18-3-dev
```

-----------------------------------------

## 설정 파일 준비
배포 전에 설정 파일을 생성해야 합니다:

```bash
# 1. ECS 파라미터 설정 파일 복사
cp cloudformation/ecs/ecs-params.txt.example cloudformation/ecs/ecs-params.txt
# 필요시 ecs-params.txt 파일을 편집하여 메모리, CPU 등 조정

# 2. SSM 시크릿 설정 파일 복사
cp cloudformation/params/ssm-values.txt.example cloudformation/params/ssm-values.txt
# ssm-values.txt 파일을 편집하여 실제 API 키와 비밀번호 입력
```

⚠️ **중요**: `ecs-params.txt`와 `ssm-values.txt`는 `.gitignore`에 포함되어 있으므로 Git에 커밋되지 않습니다.

## ECS Base 스택 배포 (ecs-base.yaml)
ECS 클러스터, IAM 역할, 로그 그룹, Service Discovery를 생성합니다.

### bash 명령어
```bash
aws cloudformation deploy \
  --stack-name skn18-3-ecs \
  --template-file cloudformation/ecs/ecs-base.yaml \
  --region ap-northeast-2 \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    NamePrefix=skn18-3-dev
```

### powershell 명령어
```powershell
aws cloudformation deploy `
  --stack-name skn18-3-ecs `
  --template-file cloudformation/ecs/ecs-base.yaml `
  --region ap-northeast-2 `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides `
    NamePrefix=skn18-3-dev
```

----------------------------

## ECS EC2 스택 배포 (ecs-ec2.yaml)
EC2 인스턴스와 ECS 서비스(Web, Celery, Redis, Postgres, Neo4j, Fuseki)를 생성합니다.

**주의**: 먼저 SSM 파라미터 스택과 Docker 이미지가 ECR에 푸시되어 있어야 합니다.

### bash 명령어
```bash
aws cloudformation deploy \
  --stack-name skn18-3-ecs-ec2 \
  --template-file cloudformation/ecs/ecs-ec2.yaml \
  --region ap-northeast-2 \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    NamePrefix=skn18-3-dev \
    InstanceType=t3.2xlarge \
    WebMemory=4096 \
    CeleryMemory=8192
```

### powershell 명령어
```powershell
aws cloudformation deploy `
  --stack-name skn18-3-ecs-ec2 `
  --template-file cloudformation/ecs/ecs-ec2.yaml `
  --region ap-northeast-2 `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides `
    NamePrefix=skn18-3-dev `
    InstanceType=t3.2xlarge `
    WebMemory=4096 `
    CeleryMemory=8192
```

----------------------------

## 배포 후 바로 확인할 것
### ecs base 스택
- ECS Cluster 생성
- CloudWatch Log Group 생성
- IAM 역할 생성 (TaskExecutionRole, TaskRole)
- Service Discovery 네임스페이스 생성

### ecs ec2 스택
- EC2 인스턴스 2대 생성 (t3.2xlarge)
- ECS 서비스 6개 생성 (web, celery, redis, postgres, neo4j, fuseki)
- Security Groups 생성
- Auto Scaling Group 생성

------------------------
## 실패 시 확인할 것
```
aws cloudformation describe-stack-events \
  --stack-name skn18-3-ecs \
  --region ap-northeast-2
```

## ECS-ECR 스택 내리기
### bash 명령어
```bash
aws cloudformation delete-stack \
  --stack-name skn18-3-ecs \
  --region ap-northeast-2
```

### powershell 명령어
```powershell
aws cloudformation delete-stack `
  --stack-name skn18-3-ecs `
  --region ap-northeast-2
```

## ECR에 Docker 이미지 push : ECR 로그인

### powershell
```powershell
docker login -u AWS --password $(aws ecr get-login-password --region ap-northeast-2) 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com
```

## ECR에 Docker 이미지 push : 도커 이미지 빌드
```powershell
docker build -t skn-backend:latest -f backend/Dockerfile .
```

```powershell
# 1. 태그 달기
docker tag skn-backend:latest 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-web:latest

# 2. 푸시하기
docker push 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-web:latest
```

## SSM 전용 스택
```powershell
aws cloudformation deploy `
  --stack-name skn18-3-params `
  --template-file infra/aws/cloudformation/params/ssm-params.yaml `
  --region ap-northeast-2 `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides `
    NamePrefix=skn18-3-dev `
    DjangoSecretKey=YOUR_DJANGO_SECRET_KEY `
    PostgresPassword=YOUR_POSTGRES_PASSWORD `
    Neo4jPassword=YOUR_NEO4J_PASSWORD `
    Neo4jAuth=neo4j/YOUR_NEO4J_PASSWORD `
    FusekiAdminPassword=YOUR_FUSEKI_ADMIN_PASSWORD `
    BotPassword=YOUR_BOT_PASSWORD `
    BotEmail=YOUR_BOT_EMAIL `
    OpenaiApiKey=YOUR_OPENAI_API_KEY `
    HfApiToken=YOUR_HF_API_TOKEN `
    LangchainApiKey=YOUR_LANGCHAIN_API_KEY `
    GeminiApiKey=YOUR_GEMINI_API_KEY `
    FalKey=YOUR_FAL_KEY `
    GoogleOauthClientSecret=YOUR_GOOGLE_OAUTH_CLIENT_SECRET `
    GoogleOauthClientId=YOUR_GOOGLE_OAUTH_CLIENT_ID
```

## 공식 이미지 미러링
```
docker pull redis:7-alpine
docker tag redis:7-alpine 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-redis:latest
docker push 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-redis:latest

docker pull pgvector/pgvector:pg16
docker tag pgvector/pgvector:pg16 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-postgres:latest
docker push 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-postgres:latest

docker pull stain/jena-fuseki:latest
docker tag stain/jena-fuseki:latest 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-fuseki:latest
docker push 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-fuseki:latest

docker pull neo4j:5.18
docker tag neo4j:5.18 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-neo4j:latest
docker push 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com/skn18-3-dev-neo4j:latest
```