import os
import pandas as pd
def save_file(df,name):
    if os.path.exists('./saved_states'):
        df.to_csv(f'./saved_states/{name}.csv', index=False)
    else:
        os.makedirs('./saved_states')
        df.to_csv(f'./saved_states/{name}.csv', index=False)
def add_to_prev(df,name):
    if os.path.exists(f'./saved_states/{name}.csv'):
        prev_df = pd.read_csv(f'./saved_states/{name}.csv')
        combined_df = pd.concat([prev_df, df], ignore_index=True)
        combined_df.to_csv(f'./saved_states/{name}.csv', index=False)
    else:
        save_file(df,name)