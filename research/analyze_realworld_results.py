#!/usr/bin/env python3                                                                                                                            
"""                                                                                                                                               
Analyze real-world evaluation results.                                                                                                            
"""                                                                                                                                               
                                                                                                                                                
import json                                                                                                                                       
import os                                                                                                                                         
from datetime import datetime                                                                                                                     
                                                                                                                                                
RESULTS_DIR = 'results'                                                                                                                           
                                                                                                                                                
# Find latest real-world evaluation                                                                                                               
result_files = [f for f in os.listdir(RESULTS_DIR) if f.startswith('realworld_eval_')]                                                            
if not result_files:                                                                                                                              
    print("No real-world evaluation results found.")                                                                                              
    print("Run: ./run_realworld_evaluation.sh")                                                                                                   
    exit(1)                                                                                                                                       
                                                                                                                                                
latest_file = sorted(result_files)[-1]                                                                                                            
results_path = os.path.join(RESULTS_DIR, latest_file)                                                                                             
                                                                                                                                                
print(f"Loading: {results_path}")                                                                                                                 
print()                                                                                                                                           
                                                                                                                                                
with open(results_path, 'r') as f:                                                                                                                
    data = json.load(f)                                                                                                                           
                                                                                                                                                
scenarios = data['scenarios']                                                                                                                     
summary = data['summary']                                                                                                                         
                                                                                                                                                
print("=" * 70)                                                                                                                                   
print("REAL-WORLD EVALUATION RESULTS")                                                                                                            
print("=" * 70)                                                                                                                                   
print()                                                                                                                                           
                                                                                                                                                
# Results table                                                                                                                                   
print(f"{'Scenario':<12} {'Type':<15} {'Predicted':<25} {'Delays (cs/sc/ml)':<20} {'Correct':<8}")                                                
print("-" * 80)                                                                                                                                   
                                                                                                                                                
for s in scenarios:                                                                                                                               
    delays = s['measured_delays']                                                                                                                 
    delay_str = f"{delays['cold_start_seconds']:.1f}/{delays['scheduling_seconds']:.1f}/{delays['metric_lag_seconds']:.1f}"                       
    correct = "correct" if s['rca_result']['correct'] else "incorrect"                                                                                          
                                                                                                                                                
    print(f"{s['scenario_id']:<12} {s['scenario_type']:<15} {s['rca_result']['predicted']:<25} {delay_str:<20} {correct:<8}")                     
                                                                                                                                                
print()                                                                                                                                           
print("-" * 70)                                                                                                                                   
print(f"Total: {summary['total_scenarios']} scenarios")                                                                                           
print(f"Correct: {summary['correct_predictions']}")                                                                                               
print(f"Accuracy: {summary['accuracy_percent']}%")                                                                                                
print()                                                                                                                                           
                                                                                                                                                
# Analyze delay patterns                                                                                                                          
print("DELAY ANALYSIS:")                                                                                                                          
print("-" * 70)                                                                                                                                   
                                                                                                                                                
for s in scenarios:                                                                                                                               
    delays = s['measured_delays']                                                                                                                 
    print(f"\n{s['scenario_id']} ({s['description']}):")                                                                                          
    print(f"  Cold Start:  {delays['cold_start_seconds']:>6.2f}s")                                                                                
    print(f"  Scheduling:  {delays['scheduling_seconds']:>6.2f}s")                                                                                
    print(f"  Metric Lag:  {delays['metric_lag_seconds']:>6.2f}s")                                                                                
    print(f"  Total Scale: {delays['total_scale_time_seconds']:>6.2f}s")                                                                          
    print(f"  Predicted:   {s['rca_result']['predicted']}")                                                                                       
                                                                                                                                                
print()                                                                                                                                           
print("=" * 70)                                                                                                                                   
print("NOTES")                                                                                                                                    
print("=" * 70)                                                                                                                                   
for note in data.get('notes', []):                                                                                                                
    print(f"  • {note}")                                                                                                                          
print()                                                                                                                                           