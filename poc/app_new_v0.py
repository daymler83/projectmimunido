# -*- coding: utf-8 -*-
"""
Created on Tue Sep 24 23:49:03 2024

@author: DOR
"""
from flask import Flask, render_template, request
import numpy as np
import pandas as pd

app = Flask(__name__)

# Cargar el archivo Excel que subiste
df = pd.read_excel('indicators.xlsx')

# Agrupar los indicadores por categoría
categories = df.groupby('Category')['Indicator'].apply(list).to_dict()

# Función para procesar los datos del formulario
def process_indicator_data(user_input_data, indicators):
    # Procesar la matriz de datos ingresada por el usuario
    data_matrix = np.array(user_input_data)

    # Normalización y cálculo de entropía (puedes ajustar según tu lógica)
    normalized_matrix = data_matrix / data_matrix.sum(axis=0)
    epsilon = 1e-9
    entropy = - np.sum(normalized_matrix * np.log(normalized_matrix + epsilon), axis=0) / np.log(len(data_matrix))
    diversity = 1 - entropy
    weights_entropy = diversity / np.sum(diversity)
    scores_entropy = np.dot(normalized_matrix, weights_entropy)

    # Crear un DataFrame con los resultados
    df_ranking = pd.DataFrame({
        'Indicator': indicators,
        'Score': scores_entropy
    }).sort_values(by='Score', ascending=False)

    return df_ranking

@app.route('/')
def index():
    # Enviar las categorías y los indicadores al HTML para generar la tabla
    return render_template('form.html', categories=categories.keys(), categories_json=categories)

@app.route('/process_data', methods=['POST'])
def process_data():
    # Obtener la categoría seleccionada
    selected_category = request.form['category']
    indicators_list = categories[selected_category]

    user_input_data = []

    # Capturar los valores ingresados en la tabla solo para la categoría seleccionada
    for indicator in indicators_list:
        relevance = int(request.form.get(f'{indicator}_r', 3))  # Verificar si existe el valor
        data_availability = int(request.form.get(f'{indicator}_d', 3))  # Verificar si existe el valor
        policy_importance = int(request.form.get(f'{indicator}_p', 3))  # Verificar si existe el valor
        user_input_data.append([relevance, data_availability, policy_importance])

    # Procesar los datos ingresados
    df_ranking = process_indicator_data(user_input_data, indicators_list)

    # Devolver la tabla de ranking solo para los indicadores de la categoría seleccionada
    return render_template('form.html', 
                           categories=categories.keys(), 
                           selected_category=selected_category,  # Mantener la categoría seleccionada
                           categories_json=categories, 
                           ranking=df_ranking.to_html(classes='table table-striped'))

if __name__ == '__main__':
    app.run(debug=True)




