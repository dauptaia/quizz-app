"""
Quiz Calibration Analysis Module

Analyzes student quiz submissions, computing calibration metrics and generating
reference models (God and Monkey) for comparison.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import ast
from pathlib import Path
from typing import List, Dict, Tuple
import random


def load_data(csv_files: List[str]) -> pd.DataFrame:
    """
    Load quiz data from CSV files.
    
    Args:
        csv_files: List of paths to CSV files
        
    Returns:
        DataFrame with all quiz submissions
    """
    dfs = []
    for file_path in csv_files:
        df = pd.read_csv(file_path)
        df['quiz_name'] = Path(file_path).stem
        dfs.append(df)
    
    combined_df = pd.concat(dfs, ignore_index=True)
    combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'])
    combined_df['answers'] = combined_df['answers'].apply(ast.literal_eval)
    
    return combined_df


def get_latest_submissions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only the most recent submission per student per quiz.
    
    Args:
        df: DataFrame with all submissions
        
    Returns:
        DataFrame with only latest submissions
    """
    df_sorted = df.sort_values('timestamp')
    latest = df_sorted.groupby(['token', 'quiz_name']).tail(1).reset_index(drop=True)
    return latest


def calculate_final_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate final score for each student per quiz.
    
    Args:
        df: DataFrame with latest submissions
        
    Returns:
        DataFrame with token, quiz_name, and final_score
    """
    scores = df[['token', 'quiz_name', 'score', 'total']].copy()
    scores['final_score'] = scores['score'].astype(str) + '/' + scores['total'].astype(str)
    return scores[['token', 'quiz_name', 'score', 'total']]


def extract_all_answers(df: pd.DataFrame, token: str) -> List[Tuple[int, int, int]]:
    """
    Extract all answers for a specific student across all quizzes.
    
    Args:
        df: DataFrame with latest submissions
        token: Student token
        
    Returns:
        List of (correct_answer, chosen_answer, confidence) tuples
    """
    student_data = df[df['token'] == token]
    all_answers = []
    for answers in student_data['answers']:
        all_answers.extend(answers)
    return all_answers


def calculate_brier_score(answers: List[Tuple[int, int, int]]) -> float:
    """
    Calculate Brier score for a set of answers.
    
    Args:
        answers: List of (correct_answer, chosen_answer, confidence) tuples
        
    Returns:
        Brier score
    """
    if not answers:
        return 0.0
    
    brier_sum = 0.0
    for correct, chosen, confidence in answers:
        correctness = 1.0 if correct == chosen else 0.0
        predicted_prob = confidence / 100.0
        brier_sum += (correctness - predicted_prob) ** 2
    
    return brier_sum / len(answers)


def bin_answers(answers: List[Tuple[int, int, int]], n_bins: int = 4) -> Dict[int, List[Tuple[int, int, int]]]:
    """
    Bin answers by confidence level (equal width).
    
    Args:
        answers: List of (correct_answer, chosen_answer, confidence) tuples
        n_bins: Number of bins
        
    Returns:
        Dictionary mapping bin index to list of answers in that bin
    """
    bin_width = 100 / n_bins
    bins = {i: [] for i in range(n_bins)}
    
    for answer in answers:
        confidence = answer[2]
        bin_idx = min(int(confidence / bin_width), n_bins - 1)
        bins[bin_idx].append(answer)
    
    return bins


def get_bin_centroids(n_bins: int = 4) -> List[float]:
    """
    Get centroid values for each bin.
    
    Args:
        n_bins: Number of bins
        
    Returns:
        List of centroid values
    """
    bin_width = 100 / n_bins
    return [bin_width * i + bin_width / 2 for i in range(n_bins)]


def compute_bin_statistics(bin_answers: List[Tuple[int, int, int]]) -> Tuple[float, float, float]:
    """
    Compute statistics for a bin: actual accuracy, +1 correct, +1 incorrect.
    
    Args:
        bin_answers: List of answers in the bin
        
    Returns:
        (actual_accuracy, accuracy_plus_one, accuracy_minus_one)
    """
    if not bin_answers:
        return (None, None, None)
    
    correct_count = sum(1 for correct, chosen, _ in bin_answers if correct == chosen)
    total = len(bin_answers)
    
    actual_accuracy = correct_count / total
    accuracy_plus_one = (correct_count + 1) / (total + 1)
    accuracy_minus_one = correct_count / (total + 1)
    
    return (actual_accuracy, accuracy_plus_one, accuracy_minus_one)


def generate_reference_answers(n_answers: int, n_bins: int, ref_type: str) -> List[Tuple[int, int, int]]:
    """
    Generate synthetic answers for reference models.
    
    Args:
        n_answers: Total number of answers to generate
        n_bins: Number of bins
        ref_type: 'god' or 'monkey'
        
    Returns:
        List of (correct_answer, chosen_answer, confidence) tuples
    """
    answers = []
    bin_width = 100 / n_bins
    answers_per_bin = n_answers // n_bins
    
    for bin_idx in range(n_bins):
        centroid = bin_width * bin_idx + bin_width / 2
        
        for _ in range(answers_per_bin):
            correct_answer = random.randint(0, 3)
            
            if ref_type == 'god':
                chosen_answer = correct_answer
            else:  # monkey
                chosen_answer = random.randint(0, 3)
            
            answers.append((correct_answer, chosen_answer, int(centroid)))
    
    return answers


def plot_calibration(student_data: Dict[str, List[Tuple[int, int, int]]], 
                     references: Dict[str, List[Tuple[int, int, int]]], 
                     n_bins: int = 4,
                     output_dir: str = 'calibration_plots'):
    """
    Plot calibration curves for all students and references.
    
    Args:
        student_data: Dictionary mapping student token to their answers
        references: Dictionary mapping reference name to their answers
        n_bins: Number of bins
        output_dir: Directory to save plots
    """
    Path(output_dir).mkdir(exist_ok=True)
    centroids = get_bin_centroids(n_bins)
    
    # Plot for each student
    for token, answers in student_data.items():
        fig, ax = plt.subplots(figsize=(10, 7))
        
        # Student data
        bins = bin_answers(answers, n_bins)
        actual, plus_one, minus_one = [], [], []
        
        for bin_idx in range(n_bins):
            stats = compute_bin_statistics(bins[bin_idx])
            try:
                actual.append(stats[0] * 100)
                plus_one.append(stats[1] * 100)
                minus_one.append(stats[2] * 100)
            except TypeError:
                actual.append(stats[0])
                plus_one.append(stats[1])
                minus_one.append(stats[2])
        
        ax.plot(centroids, actual, 'o-', linewidth=2, markersize=8, label=f'{token} - Actual', color='blue')
        ax.plot(centroids, plus_one, 's--', linewidth=1.5, markersize=6, label=f'{token} - +1 Correct', color='lightblue')
        ax.plot(centroids, minus_one, '^--', linewidth=1.5, markersize=6, label=f'{token} - +1 Incorrect', color='darkblue')
        
        # Reference data
        colors_ref = {'god': 'green', 'monkey1': 'red', 'monkey2': 'orange', 'monkey3': 'brown'}
        
        for ref_name, ref_answers in references.items():
            ref_bins = bin_answers(ref_answers, n_bins)
            ref_actual = []
            
            for bin_idx in range(n_bins):
                stats = compute_bin_statistics(ref_bins[bin_idx])
                ref_actual.append(stats[0] * 100)
            
            ax.plot(centroids, ref_actual, 'x-', linewidth=1, markersize=7, 
                   label=ref_name.capitalize(), color=colors_ref[ref_name], alpha=0.7)
        
        # Perfect calibration line
        ax.plot([0, 100], [0, 100], 'k--', linewidth=1, label='Perfect Calibration', alpha=0.3)
        
        ax.set_xlabel('Confidence Level (%)', fontsize=12)
        ax.set_ylabel('Accuracy (%)', fontsize=12)
        ax.set_title(f'Calibration Curve - Student {token}', fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-5, 105)
        ax.set_ylim(-5, 105)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/calibration_{token}.png', dpi=150)
        plt.close()


def analyze_calibration(csv_files: List[str], n_bins: int = 4, output_dir: str = 'calibration_plots'):
    """
    Main analysis function.
    
    Args:
        csv_files: List of CSV file paths
        n_bins: Number of confidence bins
        output_dir: Directory to save plots
    """
    # Load and process data
    print("Loading data...")
    df_all = load_data(csv_files)
    df = get_latest_submissions(df_all)
    
    # Calculate scores
    print("Calculating final scores...")
    scores = calculate_final_scores(df)
    print("\nFinal Scores:")
    print(scores.to_string(index=False))
    
    # Extract all students
    students = df['token'].unique()
    
    # Calculate average number of answers per student
    total_answers = sum(len(extract_all_answers(df_all, token)) for token in students)
    n_avg = int(total_answers / len(students))
    print(f"\nAverage number of answers per student: {n_avg}")
    
    # Analyze each student
    student_data = {}
    print("\nBrier Scores:")
    for token in students:
        answers = extract_all_answers(df_all, token)
        student_data[token] = answers
        brier = calculate_brier_score(answers)
        print(f"{token}: {brier:.4f}")
    
    # Generate references
    print("\nGenerating reference models...")
    n_avg = 2000
    references = {
        'god': generate_reference_answers(n_avg, n_bins, 'god'),
        'monkey1': generate_reference_answers(n_avg, n_bins, 'monkey'),
        'monkey2': generate_reference_answers(n_avg, n_bins, 'monkey'),
        'monkey3': generate_reference_answers(n_avg, n_bins, 'monkey')
    }
    
    # Plot calibration curves
    print(f"Generating calibration plots in '{output_dir}'...")
    plot_calibration(student_data, references, n_bins, output_dir)
    print(f"\nAnalysis complete! Plots saved to '{output_dir}' directory.")


if __name__ == "__main__":
    # Example usage
    csv_files = ['downloads/UNIX101_answers_filtered.csv','downloads/UNIX102_answers_filtered.csv']  # Replace with your CSV file paths
    analyze_calibration(csv_files, n_bins=4, output_dir='calibration_plots')
    