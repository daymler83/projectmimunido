from flask import Flask, render_template, jsonify, request
import numpy as np
import pandas as pd
import os

app = Flask(__name__)

# Cargar el archivo Excel una sola vez
csv_file_path = os.path.join(os.getcwd(), 'indicators.xlsx')
if os.path.exists(csv_file_path):
    df = pd.read_excel(csv_file_path)
else:
    raise FileNotFoundError(f"File not found: {csv_file_path}")

# Agrupar los indicadores por categoría
categories = df.groupby('Category')['Indicator'].apply(list).to_dict()

# Función para procesar los datos del formulario (para Page 3 - Ranking)
def process_indicator_data(user_input_data, indicators):
    data_matrix = np.array(user_input_data)

    # Normalización y cálculo de entropía
    normalized_matrix = data_matrix / data_matrix.sum(axis=0)
    epsilon = 1e-9
    entropy = - np.sum(normalized_matrix * np.log(normalized_matrix + epsilon), axis=0) / np.log(len(data_matrix))
    diversity = 1 - entropy
    weights_entropy = diversity / np.sum(diversity)
    scores_entropy = np.dot(normalized_matrix, weights_entropy)

    # Crear el DataFrame con los resultados del ranking
    df_ranking = pd.DataFrame({
        'Indicator': indicators,
        'Score': scores_entropy
    }).sort_values(by='Score', ascending=False)

    return df_ranking

# Route for Page 1 (Listing indicators by group)
@app.route('/')
def index():
    indicators = df.to_dict(orient='records')  # Convertir DataFrame a lista de diccionarios
    return render_template('index_indi.html', indicators=indicators)

# Route to get categories and indicators for the dropdowns in Page 2
@app.route('/indicators')
def get_indicators():
    return jsonify(categories)

# Route to get detailed info about a selected indicator (Page 2)
@app.route('/get_indicator_info', methods=['POST'])
def get_indicator_info():
    indicator_name = request.json['indicator']
    indicator_row = df[df['Indicator'] == indicator_name].iloc[0]  # Obtener la primera fila coincidente

    # Check if the indicator exists
    if indicator_row is not None:
        return jsonify({
            "Rationale": indicator_row['Rationale'],
            "Formula": indicator_row['Formula'],
            "Source": indicator_row['Source']
        })
    return jsonify({"error": "Indicator not found"}), 404

# Route to process data for Page 3 (Ranking)
@app.route('/process_data', methods=['POST', 'GET'])
def process_data():
    if request.method == 'GET':
        selected_category = list(categories.keys())[0]  # Mostrar la primera categoría por defecto
        return render_template('form.html', 
                               categories=categories.keys(), 
                               selected_category=selected_category, 
                               categories_json=categories)

    # Si es POST, procesa los datos enviados
    selected_category = request.form['category']
    indicators_list = categories[selected_category]
    
    user_input_data = []
    for indicator in indicators_list:
        relevance = int(request.form.get(f'{indicator}_r', 3))
        data_availability = int(request.form.get(f'{indicator}_d', 3))
        policy_importance = int(request.form.get(f'{indicator}_p', 3))
        user_input_data.append([relevance, data_availability, policy_importance])

    # Procesar los datos ingresados
    df_ranking = process_indicator_data(user_input_data, indicators_list)

    # Devolver la tabla de ranking
    return render_template('form.html', 
                           categories=categories.keys(), 
                           selected_category=selected_category, 
                           categories_json=categories, 
                           ranking=df_ranking.to_html(classes='table table-striped'))


if __name__ == '__main__':
    app.run(debug=True)
