import pandas as pd
import numpy as np

def analyze_corporation_stats(csv_file_path):
    """
    Analyze corporation ELO data to calculate win rates, average ELO gain, 
    and number of times played by corporation and player.
    
    Args:
        csv_file_path (str): Path to the corporation_elo_detailed.csv file
    """
    
    # Load the data
    print("Loading data...")
    df = pd.read_csv(csv_file_path)
    
    # Convert elo_change to numeric (in case it's stored as string)
    df['elo_change'] = pd.to_numeric(df['elo_change'])
    
    # Create win indicator (positive elo_change = win)
    df['is_win'] = df['elo_change'] > 0
    
    print(f"Total records loaded: {len(df)}")
    print(f"Date range: {df['game_date'].min()} to {df['game_date'].max()}")
    print(f"Unique corporations: {df['corporation'].nunique()}")
    print(f"Unique players: {df['player_name'].nunique()}")
    print()
    
    # Analysis by Corporation
    print("=" * 60)
    print("ANALYSIS BY CORPORATION")
    print("=" * 60)
    
    corp_stats = df.groupby('corporation').agg({
        'is_win': ['sum', 'count', 'mean'],
        'elo_change': 'mean'
    }).round(2)
    
    # Flatten column names
    corp_stats.columns = ['wins', 'games_played', 'win_rate', 'avg_elo_gain']
    corp_stats['win_rate'] = (corp_stats['win_rate'] * 100).round(1)  # Convert to percentage
    corp_stats = corp_stats.sort_values('win_rate', ascending=False)
    
    print(f"{'Corporation':<30} {'Games':<8} {'Wins':<6} {'Win Rate':<10} {'Avg ELO':<10}")
    print("-" * 70)
    for corp, row in corp_stats.iterrows():
        print(f"{corp:<30} {int(row['games_played']):<8} {int(row['wins']):<6} {row['win_rate']:<9}% {row['avg_elo_gain']:<10}")
    
    print()
    
    # Analysis by Player (top 20 most active players)
    print("=" * 80)
    print("ANALYSIS BY PLAYER (Top 20 Most Active Players)")
    print("=" * 80)
    
    player_stats = df.groupby('player_name').agg({
        'is_win': ['sum', 'count', 'mean'],
        'elo_change': 'mean'
    }).round(2)
    
    # Flatten column names
    player_stats.columns = ['wins', 'games_played', 'win_rate', 'avg_elo_gain']
    player_stats['win_rate'] = (player_stats['win_rate'] * 100).round(1)
    
    # Filter players with at least 10 games and sort by games played
    active_players = player_stats[player_stats['games_played'] >= 10].sort_values('games_played', ascending=False)
    
    print(f"{'Player':<25} {'Games':<8} {'Wins':<6} {'Win Rate':<10} {'Avg ELO':<10}")
    print("-" * 65)
    for player, row in active_players.head(20).iterrows():
        print(f"{player:<25} {int(row['games_played']):<8} {int(row['wins']):<6} {row['win_rate']:<9}% {row['avg_elo_gain']:<10}")
    
    print()
    
    # Analysis by Corporation-Player combination (top performers)
    print("=" * 90)
    print("TOP CORPORATION-PLAYER COMBINATIONS (Min 5 games, sorted by win rate)")
    print("=" * 90)
    
    corp_player_stats = df.groupby(['corporation', 'player_name']).agg({
        'is_win': ['sum', 'count', 'mean'],
        'elo_change': 'mean'
    }).round(2)
    
    # Flatten column names
    corp_player_stats.columns = ['wins', 'games_played', 'win_rate', 'avg_elo_gain']
    corp_player_stats['win_rate'] = (corp_player_stats['win_rate'] * 100).round(1)
    
    # Filter combinations with at least 5 games and sort by win rate
    top_combinations = corp_player_stats[corp_player_stats['games_played'] >= 5].sort_values('win_rate', ascending=False)
    
    print(f"{'Corporation':<25} {'Player':<20} {'Games':<6} {'Wins':<5} {'Win Rate':<9} {'Avg ELO':<8}")
    print("-" * 85)
    for (corp, player), row in top_combinations.head(25).iterrows():
        corp_short = corp[:24] if len(corp) > 24 else corp
        player_short = player[:19] if len(player) > 19 else player
        print(f"{corp_short:<25} {player_short:<20} {int(row['games_played']):<6} {int(row['wins']):<5} {row['win_rate']:<8}% {row['avg_elo_gain']:<8}")
    
    print()
    
    # Summary statistics
    print("=" * 50)
    print("SUMMARY STATISTICS")
    print("=" * 50)
    
    total_games = len(df)
    total_wins = df['is_win'].sum()
    overall_win_rate = (total_wins / total_games * 100).round(1)
    avg_elo_change = df['elo_change'].mean().round(2)
    
    print(f"Total games analyzed: {total_games}")
    print(f"Total wins: {total_wins}")
    print(f"Overall win rate: {overall_win_rate}%")
    print(f"Average ELO change: {avg_elo_change}")
    print(f"ELO change range: {df['elo_change'].min()} to {df['elo_change'].max()}")
    
    # Best and worst performing corporations
    best_corp = corp_stats.index[0]
    worst_corp = corp_stats.index[-1]
    
    print(f"\nBest performing corporation: {best_corp} ({corp_stats.loc[best_corp, 'win_rate']}% win rate)")
    print(f"Worst performing corporation: {worst_corp} ({corp_stats.loc[worst_corp, 'win_rate']}% win rate)")
    
    # Most active player
    most_active_player = active_players.index[0]
    print(f"Most active player: {most_active_player} ({int(active_players.loc[most_active_player, 'games_played'])} games)")
    
    return corp_stats, player_stats, corp_player_stats

if __name__ == "__main__":
    # Run the analysis
    csv_file = "analysis/corporation_elo_detailed.csv"
    
    try:
        corp_stats, player_stats, corp_player_stats = analyze_corporation_stats(csv_file)
        print("\nAnalysis completed successfully!")
        
        # Optionally save results to CSV files
        save_results = input("\nWould you like to save the results to CSV files? (y/n): ").lower().strip()
        if save_results == 'y':
            corp_stats.to_csv("analysis/corporation_stats.csv")
            player_stats.to_csv("analysis/player_stats.csv")
            corp_player_stats.to_csv("analysis/corporation_player_stats.csv")
            print("Results saved to CSV files in the analysis/ directory.")
            
    except FileNotFoundError:
        print(f"Error: Could not find the file '{csv_file}'")
        print("Please make sure the file exists in the correct location.")
    except Exception as e:
        print(f"An error occurred: {e}")
