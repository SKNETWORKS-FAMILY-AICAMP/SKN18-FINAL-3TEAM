## aws 계정과 연결
```
aws sts get-caller-identity
```

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

## ecs-ecr 배포
### bash 명령어
```bash
aws cloudformation deploy \
  --stack-name skn18-3-ecs \
  --template-file ecs-ecr.yaml \
  --region ap-northeast-2 \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    NamePrefix=skn18-3-dev
```

### powershell 명령어
```powershell
aws cloudformation deploy `
  --stack-name skn18-3-ecs `
  --template-file ecs-ecr.yaml `
  --region ap-northeast-2 `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides `
    NamePrefix=skn18-3-dev
```

----------------------------

## 배포 후 바로 확인할 것
### ecs 스택
- ECR repo 4개 생성
- ECS Cluster 생성
- CloudWatch Log Group 생성

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
docker login -u AWS --password-stdin $(aws ecr get-login-password --region ap-northeast-2) 533124807326.dkr.ecr.ap-northeast-2.amazonaws.com
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