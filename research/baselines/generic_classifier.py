#!/usr/bin/env python3                                                                                                                            
"""                                                                                                                                               
Generic Baseline Classifier                                                                                                                       
                                                                                                                                                
Represents existing "generic" RCA tools that:                                                                                                     
- Do NOT use KEDA-specific signals                                                                                                                
- Cannot distinguish between root cause types                                                                                                     
- Only detect "scaling is slow" without explanation                                                                                               
"""                                                                                                                                               
                                                                                                                                                
import json                                                                                                                                       
import sys                                                                                                                                        
                                                                                                                                                
# Generic baseline: uses total delay only, no root cause distinction                                                                              
SLOW_THRESHOLD_SECONDS = 5.0                                                                                                                      
                                                                                                                                                
def classify_generic(cold_start_ms, scheduling_ms, metric_lag_ms):                                                                                
    """                                                                                                                                           
    Generic classifier that does NOT distinguish root causes.                                                                                     
    Returns either "SCALING_DELAY" or "NORMAL" based on total delay.                                                                              
    """                                                                                                                                           
    total_delay_seconds = (cold_start_ms + scheduling_ms) / 1000.0                                                                                
                                                                                                                                                
    if total_delay_seconds > SLOW_THRESHOLD_SECONDS:                                                                                              
        return {                                                                                                                                  
            "root_cause": "SCALING_DELAY",  # Generic, non-specific                                                                               
            "confidence": 0.5,                                                                                                                    
            "evidence": f"Total scaling delay: {total_delay_seconds:.1f}s exceeds threshold",                                                     
            "recommendation": "Check system performance"  # Generic recommendation                                                                
        }                                                                                                                                         
    else:                                                                                                                                         
        return {                                                                                                                                  
            "root_cause": "NORMAL",                                                                                                               
            "confidence": 0.5,                                                                                                                    
            "evidence": f"Total delay {total_delay_seconds:.1f}s within threshold",                                                               
            "recommendation": "No action needed"                                                                                                  
        }                                                                                                                                         
                                                                                                                                                
                                                                                                                                                
def classify_threshold_based(cold_start_ms, scheduling_ms, metric_lag_ms):                                                                        
    """                                                                                                                                           
    Threshold-based classifier (slightly better generic approach).                                                                                
    Uses independent thresholds but lacks KEDA context.                                                                                           
    """                                                                                                                                           
    # Simple thresholds without KEDA-awareness                                                                                                    
    COLD_START_THRESHOLD = 10000  # 10s                                                                                                           
    SCHEDULING_THRESHOLD = 5000   # 5s                                                                                                            
                                                                                                                                                
    cold_start_s = cold_start_ms / 1000.0                                                                                                         
    scheduling_s = scheduling_ms / 1000.0                                                                                                         
                                                                                                                                                
    # Check thresholds independently                                                                                          
    issues = []                                                                                                                                   
    if cold_start_ms > COLD_START_THRESHOLD:                                                                                                      
        issues.append(f"container_slow ({cold_start_s:.1f}s)")                                                                                    
    if scheduling_ms > SCHEDULING_THRESHOLD:                                                                                                      
        issues.append(f"scheduling_slow ({scheduling_s:.1f}s)")                                                                                   
                                                                                                                                                
    if not issues:                                                                                                                                
        return {                                                                                                                                  
            "root_cause": "NORMAL",                                                                                                               
            "confidence": 0.5,                                                                                                                    
            "evidence": "No thresholds exceeded",                                                                                                 
            "recommendation": "No action needed"                                                                                                  
        }                                                                                                                                         
                                                                                                                                                
    # Returns generic issue list, NOT specific root cause                                                                                         
    return {                                                                                                                                      
        "root_cause": "PERFORMANCE_ISSUE",  # Generic                                                                                             
        "confidence": 0.6,                                                                                                                        
        "evidence": f"Issues detected: {', '.join(issues)}",                                                                                      
        "recommendation": "Investigate performance"                                                                                               
    }                                                                                                                                             
                                                                                                                                                
                                                                                                                                                
if __name__ == "__main__":                                                                                                                        
    # Test with sample data                                                                                                                       
    test_cases = [                                                                                                                                
        {"cold_start_ms": 12000, "scheduling_ms": 2000, "metric_lag_ms": 5000},  # Should be COLD_START                                           
        {"cold_start_ms": 3000, "scheduling_ms": 8000, "metric_lag_ms": 4000},   # Should be SCHEDULING                                           
        {"cold_start_ms": 5000, "scheduling_ms": 3000, "metric_lag_ms": 20000},  # Should be METRIC_LAG                                           
    ]                                                                                                                                             
                                                                                                                                                
    print("Generic Baseline Classification Results:")                                                                                             
    print("=" * 60)                                                                                                                               
    for tc in test_cases:                                                                                                                         
        result = classify_generic(**tc)                                                                                                           
        print(f"Input: {tc}")                                                                                                                     
        print(f"Generic Result: {result['root_cause']}")                                                                                          
        print()