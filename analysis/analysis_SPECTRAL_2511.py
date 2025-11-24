"""
Quiz Calibration Analysis Module

Analyzes student quiz submissions, computing calibration metrics and generating
reference models (God and Monkey) for comparison.
"""

import pandas as pd
import ast
import yaml
from pathlib import Path
from typing import List, Tuple


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




def compute_all_scores(csv_files: List[str], naming_users_yaml:str):
    """
    Main analysis function.
    
    Args:
        csv_files: List of CSV file paths
        n_bins: Number of confidence bins
        output_dir: Directory to save plots
    """
    # Load and process data
    print("Loading users...")
    with open(naming_users_yaml, "r") as fin:
        users_naming = yaml.safe_load(fin)["users"]
    
    print(users_naming)
    print("Loading data...")
    df_all = load_data(csv_files)
    df = get_latest_submissions(df_all)
    
    # Calculate scores
    print("Calculating final scores...")
    scores = calculate_final_scores(df)


    scores['token'] = scores['token'].map(users_naming).fillna(scores['token'])
    print("\nFinal Scores:")
    print(scores.to_string(index=False))
    
    

if __name__ == "__main__":
    # Example usage
    csv_files = ['downloads/SPECTRAL101_answers.csv']  # Replace with your CSV file paths
    naming_users_yaml = "../secret_auth_users.yaml"
    compute_all_scores(csv_files, naming_users_yaml)
    