# BL-31.6.a Nachweis: UI-Artefaktpfad + Task-Revision (dev)

## Scope
Issue #345 (`BL-31.6.a`):
- ECR-Repository `swisstopo-dev-ui`
- UI-Image Build/Push mit reproduzierbarem Tag
- ECS-Task-Definition `swisstopo-dev-ui` mit gültiger Image-Revision

## Reproduzierbarer Lauf

```bash
IMAGE_TAG=$(git rev-parse --short HEAD) \
APP_VERSION=$(git rev-parse --short HEAD) \
UI_API_BASE_URL=https://api.geo.friedland.ai \
./scripts/setup_bl31_ui_artifact_path.sh
```

Der Lauf erzeugt eine maschinenlesbare Evidenzdatei unter `artifacts/bl31/`.

## Ergebnis (2026-02-28)

Evidence-Datei:
- `artifacts/bl31/20260228T075535Z-bl31-ui-artifact-path.json`

Extrakt:
- CodeBuild: `swisstopo-dev-api-openclaw-build:a9976f70-2f9d-4cb8-b0cd-44d8ab8cc5a1` (SUCCEEDED)
- LogStream: `a9976f70-2f9d-4cb8-b0cd-44d8ab8cc5a1`
- ECR Image: `523234426229.dkr.ecr.eu-central-1.amazonaws.com/swisstopo-dev-ui:561a5d1`
- Image Digest: `sha256:88a792bc54953016ffc299b4848f19b75f76ff502a4421f29c379c920decf2da`
- ECS Task Definition: `arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-ui:3`

## Verifikation (read-only)

```bash
aws ecr describe-images \
  --region eu-central-1 \
  --repository-name swisstopo-dev-ui \
  --image-ids imageTag=561a5d1

aws ecs describe-task-definition \
  --region eu-central-1 \
  --task-definition swisstopo-dev-ui:3
```

Erwartung:
- ECR-Image ist `ACTIVE` und Tag/Digest sind auflösbar.
- Taskdef `swisstopo-dev-ui:3` referenziert dasselbe Image.
