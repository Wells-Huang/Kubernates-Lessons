{{- define "task6-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "task6-platform.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s" (include "task6-platform.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "task6-platform.labels" -}}
app.kubernetes.io/name: {{ include "task6-platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "task6-platform.redisAuthSecretName" -}}
{{- printf "%s-redis-auth" (include "task6-platform.fullname" .) -}}
{{- end -}}

{{- define "task6-platform.webServiceName" -}}
{{- printf "%s-web" (include "task6-platform.fullname" .) -}}
{{- end -}}

{{- define "task6-platform.nginxServiceName" -}}
{{- printf "%s-nginx" (include "task6-platform.fullname" .) -}}
{{- end -}}

{{- define "task6-platform.nginxConfigName" -}}
{{- printf "%s-nginx-config" (include "task6-platform.fullname" .) -}}
{{- end -}}

{{- define "task6-platform.redisServiceName" -}}
{{- printf "%s-redis" (include "task6-platform.fullname" .) -}}
{{- end -}}

{{- define "task6-platform.redisHeadlessServiceName" -}}
{{- printf "%s-redis-headless" (include "task6-platform.fullname" .) -}}
{{- end -}}

{{- define "task6-platform.redisTargetHost" -}}
{{- printf "%s-%d.%s.%s.svc.cluster.local" (include "task6-platform.redisServiceName" .) (.Values.redis.auth.hostPodOrdinal | int) (include "task6-platform.redisHeadlessServiceName" .) .Release.Namespace -}}
{{- end -}}

{{- define "task6-platform.redisClusterServiceHost" -}}
{{- printf "%s.%s.svc.cluster.local" (include "task6-platform.redisServiceName" .) .Release.Namespace -}}
{{- end -}}
