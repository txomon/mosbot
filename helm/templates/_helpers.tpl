{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "mosbot-chart.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/* Generate PostgreSQL database URL */}}
{{- define "mosbot-chart.databaseurl" -}}
  postgresql://
  {{- .Values.postgresql.postgresqlUsername -}}:
  {{- .Values.postgresql.postgresqlPassword -}}@
  {{- .Release.Name }}-postgresql.
  {{- .Release.Namespace -}}/
  {{- .Values.postgresql.postgresqlDatabase -}}
{{- end -}}
