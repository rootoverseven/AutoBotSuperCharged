import pandas as pd

def generate_excel_report(trades):
    df = pd.DataFrame(trades, columns=['Symbol', 'Entry Time', 'Exit Time', 'Position', 'Entry Price', 'Exit Price', 'Quantity', 'P/L'])
    df['P/L'] = df['P/L'].astype(float)
    total_pnl = df['P/L'].sum()

    with pd.ExcelWriter('reports/trading_report.xlsx', engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Trades', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['Trades']
        
        # Add summary
        worksheet['A{}'.format(len(df) + 3)] = 'Total P/L'
        worksheet['B{}'.format(len(df) + 3)] = total_pnl
        
        # Add formatting
        for column in worksheet.columns:
            max_length = 0
            column = [cell for cell in column]
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

    print(f"Excel report generated: reports/trading_report.xlsx")