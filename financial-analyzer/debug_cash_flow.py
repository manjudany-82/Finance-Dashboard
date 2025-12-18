from microsoft_excel import ExcelHandler

# Load data
dfs = ExcelHandler.load_data('onedrive')
df = dfs.get('Cash flow')

print('Total rows:', len(df))
print('\nAll rows with index:')
for idx, row in df.iterrows():
    print(f'{idx}: {row.iloc[0]} | {row.iloc[1]}')
