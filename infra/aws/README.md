# OFFMate AWS MVP

This stack deploys only the MVP serverless path:

- API Gateway REST API + Cognito
- Lambda FastAPI adapter
- DynamoDB on-demand single table
- private S3 proof bucket with a one-day lifecycle
- Step Functions + Lambda RunPod VLM analysis worker
- Secrets Manager for the backend-only RunPod key

It intentionally does not create EC2, NAT Gateway, RDS, Neptune, or SNS.

```bash
cd infra/aws
sam build --template-file template.yaml
sam deploy --config-env dev --profile OFFMateDev
```

After deployment, replace the placeholder value in the
`offmate/dev/runpod-api-key` secret from the AWS console. Never put the key in
the repository, iOS application, shell history, or CloudFormation parameters.
