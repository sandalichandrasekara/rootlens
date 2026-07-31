package types

// SubCauseExplanation contains feature importance for sub-cause prediction
type SubCauseExplanation struct {
	TopFeatures []FeatureContribution `json:"top_features"`
	Summary     string                `json:"summary"`
}

// FeatureContribution represents a feature's contribution to the sub-cause prediction.
// Importance is the RandomForest global feature importance (impurity-based, sums to 1.0).
type FeatureContribution struct {
	Feature    string  `json:"feature"`
	Value      float64 `json:"value"`
	Importance float64 `json:"importance"`
}
