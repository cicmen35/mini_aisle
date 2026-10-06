# syntax=docker/dockerfile:1.7
# Terraform + the infra code, used to provision LocalStack from docker compose and from kind.
FROM hashicorp/terraform:1.9.8
RUN addgroup -S -g 10001 tf && adduser -S -u 10001 -G tf -h /work tf \
 && mkdir -p /work && chown tf:tf /work
COPY --chown=tf:tf infra/terraform /infra
USER 10001:10001
ENV TF_DATA_DIR=/work/.terraform TF_IN_AUTOMATION=1 TF_PLUGIN_CACHE_DIR=/work/plugin-cache
WORKDIR /infra/envs/localstack
ENTRYPOINT ["/infra/scripts/localstack-entrypoint.sh"]
CMD ["apply"]
