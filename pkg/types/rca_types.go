package types

import "math"

func round4(f float64) float64 {
	return math.Round(f*10000) / 10000
}

// EnhancedRCAResult contains both rule-based and ML sub-cause results.
// FinalConfidence = (RuleBasedConfidence × 0.6) + (MLConfidence × 0.4) when ML succeeds;
// falls back to RuleBasedConfidence alone when ML is unavailable.
type EnhancedRCAResult struct {
	// Rule-based classification
	RootCause           string  `json:"root_cause"`
	RuleBasedConfidence float64 `json:"rule_based_confidence"`

	// ML sub-cause explanation (category-specific explainer)
	MLConfidence            float64              `json:"ml_confidence"`
	SubCause                string               `json:"sub_cause,omitempty"`
	SubCauseConfidence      float64              `json:"sub_cause_confidence,omitempty"`
	SubCauseProbabilities   map[string]float64   `json:"sub_cause_probabilities,omitempty"`
	SubCauseExplanation     *SubCauseExplanation `json:"sub_cause_explanation,omitempty"`
	SubCauseRecommendations []string             `json:"sub_cause_recommendations,omitempty"`

	// Combined result
	FinalConfidence float64 `json:"final_confidence"`
	MethodAgreement string  `json:"method_agreement"`

	// Details
	Details         string   `json:"details,omitempty"`
	Timestamp       string   `json:"timestamp,omitempty"`
	DetectedAt      string   `json:"detected_at,omitempty"`
	Evidence        []string `json:"evidence,omitempty"`
	Recommendations []string `json:"recommendations,omitempty"`
}

// Round rounds all confidence and probability float fields to 4 decimal places
// so JSON output is clean regardless of ML model floating-point precision.
func (r *EnhancedRCAResult) Round() {
	r.RuleBasedConfidence = round4(r.RuleBasedConfidence)
	r.MLConfidence = round4(r.MLConfidence)
	r.SubCauseConfidence = round4(r.SubCauseConfidence)
	r.FinalConfidence = round4(r.FinalConfidence)
	for k, v := range r.SubCauseProbabilities {
		r.SubCauseProbabilities[k] = round4(v)
	}
	if r.SubCauseExplanation != nil {
		for i := range r.SubCauseExplanation.TopFeatures {
			r.SubCauseExplanation.TopFeatures[i].Importance = round4(r.SubCauseExplanation.TopFeatures[i].Importance)
		}
	}
}
