# syntax=docker/dockerfile:1.7
# Terraform + the infra code, used to provision LocalStack from docker compose and from kind.
# Providers are baked in as a filesystem mirror, so `terraform init` needs no internet access
# (the kind NetworkPolicy doesn't allow it).
FROM hashicorp/terraform:1.9.8
COPY infra/terraform /infra
RUN export TF_DATA_DIR=/tmp/tf-build \
 && terraform -chdir=/infra/envs/localstack init -backend=false -input=false >/dev/null \
 && terraform -chdir=/infra/envs/localstack providers mirror /opt/tf-mirror \
 && rm -rf /tmp/tf-build \
 && printf 'provider_installation {\n  filesystem_mirror {\n    path = "/opt/tf-mirror"\n  }\n}\n' > /etc/terraformrc \
 && addgroup -S -g 10001 tf && adduser -S -u 10001 -G tf -h /work tf \
 && mkdir -p /work && chown tf:tf /work
USER 10001:10001
ENV TF_CLI_CONFIG_FILE=/etc/terraformrc TF_DATA_DIR=/work/.terraform TF_IN_AUTOMATION=1
WORKDIR /infra/envs/localstack
ENTRYPOINT ["/infra/scripts/localstack-entrypoint.sh"]
CMD ["apply"]
