# RootLens Test Results Summary

**Date:** 2026-03-28
**Platform:** macOS Darwin 24.5.0
**Go Version:** 1.25 | **Python Version:** 3.9.6 | **Node Version:** 20.x
**Branch:** main
**Commit:** ef773b9

---

## 1. Unit Tests

Unit tests validate individual components in isolation — functions, extractors, validators, and controller logic.

### 1.1 Go API Validation Tests
**File:** `pkg/api/validation_test.go`
**Log:** `unit_tests_go.log`

| Test | Result |
|------|--------|
| TestValidateWorkloadRequest/valid_spike_request | PASS |
| TestValidateWorkloadRequest/valid_sustained_request | PASS |
| TestValidateWorkloadRequest/count_too_high | PASS |
| TestValidateWorkloadRequest/count_zero | PASS |
| TestValidateWorkloadRequest/size_too_large | PASS |
| TestValidateWorkloadRequest/invalid_mode | PASS |
| TestValidateWorkloadRequest/default_mode | PASS |
| TestValidateTestRCARequest/valid_request | PASS |
| TestValidateTestRCARequest/negative_cold_start_delay | PASS |
| TestValidateTestRCARequest/cold_start_delay_too_high | PASS |
| TestValidateTestRCARequest/negative_queue_depth | PASS |
| TestValidateTestRCARequest/replicas_too_high | PASS |

**Result: 12/12 PASSED**

### 1.2 Go RCA Engine Tests
**File:** `pkg/rca/engine_test.go`
**Log:** `unit_tests_go.log`

| Test | Result |
|------|--------|
| TestAnalyzeNoPods | PASS |
| TestAnalyzeColdStart | PASS |
| TestAnalyzeSchedulingDelay | PASS |
| TestAnalyzeMetricLag | PASS |

**Result: 4/4 PASSED**

### 1.3 Go Collector Tests
**File:** `pkg/collector/rabbitmq_test.go`
**Log:** `unit_tests_go.log`

| Test | Result |
|------|--------|
| TestRabbitMQCollector | PASS |

**Result: 1/1 PASSED**

### 1.4 Kubernetes Operator Controller Tests
**File:** `operator/internal/controller/rootlens_controller_test.go`
**Log:** `unit_tests_operator.log`
**Framework:** Ginkgo v2 + envtest (controller-runtime test environment)

| Spec | Result |
|------|--------|
| Spec 1 - Reconcile creates resources | PASS |
| Spec 2 - Reconcile updates status | PASS |
| Spec 3 - Reconcile handles deletion | PASS |
| Spec 4 - Reconcile handles missing CR | PASS |
| Spec 5 - Reconcile sets owner references | PASS |
| Spec 6 - Reconcile idempotent re-runs | PASS |

**Result: 6/6 PASSED**

### 1.5 ML Feature Extractor Tests
**File:** `ml-integration/tests/test_feature_extractors.py`
**Log:** `unit_tests_ml.log`
**Framework:** pytest

| Test | Result |
|------|--------|
| ColdStartFeatureExtractor::test_output_shape | PASS |
| ColdStartFeatureExtractor::test_feature_count_matches_names | PASS |
| ColdStartFeatureExtractor::test_no_nan_with_empty_input | PASS |
| ColdStartFeatureExtractor::test_no_nan_with_zero_total_cold_start | PASS |
| ColdStartFeatureExtractor::test_realistic_input | PASS |
| ColdStartFeatureExtractor::test_nan_input_sanitized | PASS |
| ColdStartFeatureExtractor::test_inf_input_sanitized | PASS |
| ColdStartFeatureExtractor::test_dtype_is_float64 | PASS |
| ColdStartFeatureExtractor::test_get_sub_causes_returns_list | PASS |
| ColdStartFeatureExtractor::test_recommendations_returned_for_all_sub_causes | PASS |
| SchedulingFeatureExtractor::test_output_shape | PASS |
| SchedulingFeatureExtractor::test_feature_count_matches_names | PASS |
| SchedulingFeatureExtractor::test_no_nan_with_empty_input | PASS |
| SchedulingFeatureExtractor::test_resource_pressure_zero_cpu | PASS |
| SchedulingFeatureExtractor::test_realistic_scheduling_delay | PASS |
| SchedulingFeatureExtractor::test_infer_sub_cause_from_reason | PASS |
| SchedulingFeatureExtractor::test_get_sub_causes_returns_list | PASS |
| MetricPropagationFeatureExtractor::test_output_shape | PASS |
| MetricPropagationFeatureExtractor::test_feature_count_matches_names | PASS |
| MetricPropagationFeatureExtractor::test_no_nan_with_empty_input | PASS |
| MetricPropagationFeatureExtractor::test_zero_polling_interval_no_divide_by_zero | PASS |
| MetricPropagationFeatureExtractor::test_alternative_field_names | PASS |
| MetricPropagationFeatureExtractor::test_queue_depth_fallback | PASS |
| MetricPropagationFeatureExtractor::test_realistic_keda_lag | PASS |
| MetricPropagationFeatureExtractor::test_infer_sub_cause_keda_polling | PASS |
| MetricPropagationFeatureExtractor::test_infer_sub_cause_metrics_server | PASS |

**Result: 26/26 PASSED**

### Unit Test Totals

| Component | Tests | Passed | Failed |
|-----------|-------|--------|--------|
| Go API Validation | 12 | 12 | 0 |
| Go RCA Engine | 4 | 4 | 0 |
| Go Collector | 1 | 1 | 0 |
| Operator Controller | 6 | 6 | 0 |
| ML Feature Extractors | 26 | 26 | 0 |
| **Total** | **49** | **49** | **0** |

---

## 2. Integration Tests

Integration tests validate cross-component interactions — Go RCA engine calling the Python ML service, model loading with trained artifacts, and end-to-end prediction pipelines.

### 2.1 Go-to-Python ML Integration (RCA Engine + Flask Explainers)
**File:** `pkg/rca/engine_integration_test.go`
**Log:** `integration_tests_go_rca.log`
**Requires:** ML Flask service running on localhost:5000

| Test | Root Cause | Rule Conf | ML Conf | Final Conf | Result |
|------|-----------|-----------|---------|------------|--------|
| TestIntegration_ColdStartWithSubCause | POD_COLD_START | 0.85 | 0.41 | 0.85 | PASS |
| TestIntegration_SchedulingWithSubCause | SCHEDULING_CONTENTION | 0.80 | 0.71 | 0.76 | PASS |
| TestIntegration_MetricPropagationWithSubCause | METRIC_PROPAGATION_LAG | 0.75 | 0.77 | 0.76 | PASS |
| TestIntegration_ExplainersStatus | N/A | N/A | N/A | N/A | PASS |

**Key Observations:**
- Confidence combination formula verified: Final = (Rule x 0.6) + (ML x 0.4)
- Cold Start sub-cause marked as "undetermined" due to low ML confidence (0.41 < 0.5 threshold)
- All 3 explainer endpoints (cold-start, scheduling, metric-propagation) responding correctly
- Graceful fallback behavior validated

**Result: 4/4 PASSED**

### 2.2 ML Model Loading & Prediction Pipeline
**File:** `ml-integration/tests/test_model_loading.py`
**Log:** `integration_tests_ml_models.log`
**Tests:** Model-Scaler-Extractor alignment, prediction validity, probability distributions

| Test | Result |
|------|--------|
| ColdStartModel::test_model_feature_count_matches_extractor | PASS |
| ColdStartModel::test_scaler_feature_count_matches_extractor | PASS |
| ColdStartModel::test_predict_returns_valid_class | PASS |
| ColdStartModel::test_predict_proba_sums_to_one | PASS |
| ColdStartModel::test_predict_proba_shape | PASS |
| ColdStartModel::test_no_prediction_error_on_nan_sanitized_input | PASS |
| SchedulingModel::test_model_feature_count_matches_extractor | PASS |
| SchedulingModel::test_scaler_feature_count_matches_extractor | PASS |
| SchedulingModel::test_predict_returns_valid_class | PASS |
| SchedulingModel::test_predict_proba_sums_to_one | PASS |
| MetricPropagationModel::test_model_feature_count_matches_extractor | PASS |
| MetricPropagationModel::test_scaler_feature_count_matches_extractor | PASS |
| MetricPropagationModel::test_predict_returns_valid_class | PASS |
| MetricPropagationModel::test_predict_proba_sums_to_one | PASS |
| MetricPropagationModel::test_feature_importances_available | PASS |

**Key Observations:**
- All 3 trained models (Cold Start, Scheduling, Metric Propagation) load correctly
- Feature counts match between model, scaler, and extractor for each category
- Prediction probabilities sum to 1.0 (valid probability distributions)
- Models handle sanitized NaN inputs without errors

**Result: 15/15 PASSED**

### Integration Test Totals

| Component | Tests | Passed | Failed |
|-----------|-------|--------|--------|
| Go-Python RCA Integration | 4 | 4 | 0 |
| ML Model Loading Pipeline | 15 | 15 | 0 |
| **Total** | **19** | **19** | **0** |

---

## 3. System Tests

System tests validate the deployment infrastructure — Kubernetes manifests, Helm charts, CRDs, and production readiness.

### 3.1 Helm Chart Validation
**Log:** `system_tests.log`

| Check | Result |
|-------|--------|
| Helm lint (rootlens-operator chart) | PASS (0 charts failed) |
| Helm template dry-run (8 K8s resources rendered) | PASS |

**Resources validated via Helm template:**
- ServiceAccount
- CustomResourceDefinition (rootlens.rca.rootlens.io)
- ClusterRole (manager-role)
- ClusterRoleBinding (manager-rolebinding)
- Role (leader-election-role)
- RoleBinding (leader-election-rolebinding)
- Service (metrics)
- Deployment (operator)

### 3.2 Kustomize Manifest Validation
**Log:** `system_tests.log`

| Check | Result |
|-------|--------|
| Kustomize build (operator/config/default) | VALID |

### 3.3 Kubernetes Manifest Dry-Run (Raw Manifests)
**Log:** `system_tests.log`

| Resource | Type | Result |
|----------|------|--------|
| rootlens-api | Deployment + Service | configured (dry run) |
| rootlens-config | ConfigMap | configured (dry run) |
| rabbitmq-consumer | Deployment | configured (dry run) |
| rootlens-dashboard | Deployment + Service | configured (dry run) |
| rabbitmq-trigger-auth | TriggerAuthentication (KEDA) | configured (dry run) |
| rabbitmq-consumer-scaler | ScaledObject (KEDA) | configured (dry run) |
| ml-service | Deployment + Service | configured (dry run) |
| rootlens-api | ServiceMonitor (Prometheus) | configured (dry run) |
| rabbitmq | ConfigMap + Service + StatefulSet | configured (dry run) |

**Result: 14/14 resources validated**

### 3.4 Production Custom Resource Validation
**Log:** `system_tests.log`

| Check | Result |
|-------|--------|
| Production CR dry-run (rca_v1alpha1_rootlens_ghcr.yaml) | created (dry run) |

### System Test Totals

| Validation | Checks | Passed | Failed |
|------------|--------|--------|--------|
| Helm Chart Lint | 1 | 1 | 0 |
| Helm Template Dry-Run | 8 | 8 | 0 |
| Kustomize Validation | 1 | 1 | 0 |
| K8s Manifest Dry-Run | 14 | 14 | 0 |
| Production CR Dry-Run | 1 | 1 | 0 |
| **Total** | **25** | **25** | **0** |

---

## Overall Summary

| Test Level | Total Tests | Passed | Failed | Pass Rate |
|------------|-------------|--------|--------|-----------|
| Unit Tests | 49 | 49 | 0 | 100% |
| Integration Tests | 19 | 19 | 0 | 100% |
| System Tests | 25 | 25 | 0 | 100% |
| **Grand Total** | **93** | **93** | **0** | **100%** |

### Test Coverage by Component

| Component | Unit | Integration | System | Total |
|-----------|------|-------------|--------|-------|
| Go API Server | 12 | - | 2 | 14 |
| Go RCA Engine | 4 | 4 | - | 8 |
| Go Collector | 1 | - | - | 1 |
| Kubernetes Operator | 6 | - | 10 | 16 |
| ML Service (Python) | 26 | 15 | - | 41 |
| K8s Manifests | - | - | 14 | 14 |
| **Total** | **49** | **19** | **25** | **93** (1 shared) |

### Tools & Frameworks Used

| Tool | Purpose |
|------|---------|
| `go test` | Go unit and integration testing |
| `pytest` | Python ML service testing |
| `Ginkgo v2 + envtest` | Kubernetes operator controller testing |
| `helm lint` | Helm chart validation |
| `kubectl kustomize` | Kustomize manifest validation |
| `kubectl apply --dry-run=client` | Kubernetes manifest syntax and schema validation |
| `helm template` | Helm chart rendering and validation |

### Evidence Files

| File | Description |
|------|-------------|
| `unit_tests_go.log` | Go backend unit test output (API, Collector, RCA) |
| `unit_tests_operator.log` | Kubernetes operator controller test output |
| `unit_tests_ml.log` | ML feature extractor unit test output |
| `integration_tests_go_rca.log` | Go-to-Python RCA integration test output |
| `integration_tests_ml_models.log` | ML model loading and prediction test output |
| `system_tests.log` | Helm, Kustomize, and K8s manifest validation output |
