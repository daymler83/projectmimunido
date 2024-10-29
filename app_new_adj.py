from flask import Flask, render_template, jsonify, request, send_file
from markupsafe import Markup
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import numpy as np
import pandas as pd
import os
import io

app = Flask(__name__)

# Configuración de la base de datos SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///indicators_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo para los datos de entrada
class IndicatorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    indicator = db.Column(db.String(100), nullable=False)
    relevance = db.Column(db.Integer, nullable=False)
    data_availability = db.Column(db.Integer, nullable=False)
    data_quality = db.Column(db.Integer, nullable=False)
    policy_importance = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Inicializar la base de datos
with app.app_context():
    #db.drop_all()
    db.create_all()

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

# Ruta para exportar los datos guardados a CSV
@app.route('/export_data')
def export_data():
    # Obtener todos los datos de la base de datos
    data = IndicatorData.query.all()

    # Convertir los datos en un DataFrame de pandas
    rows = [{
        'category': d.category,
        'indicator': d.indicator,
        'relevance': d.relevance,
        'data_availability': d.data_availability,
        'data_quality': d.data_quality,
        'policy_importance': d.policy_importance,
        'timestamp': d.timestamp
    } for d in data]
    
    df = pd.DataFrame(rows)

    # Crear un archivo CSV en memoria
    output = io.BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)

    # Enviar el archivo CSV para su descarga
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='indicator_data.csv')  

@app.route('/')
def home():
    return render_template('index_indi_adj.html', categories=categories, show_presentation=True)

# Route to render Page 2 (back from Page 3)
@app.route('/indicator_list', methods=['GET'])
def indicators_list():
    return render_template('index_indi_adj.html', categories=categories, show_presentation=False)  # Replace with your Page 2 template

# Route para obtener las categorías e indicadores para los dropdowns en la página 2
@app.route('/indicators')
def get_indicators():
    return jsonify(categories)

# Route para obtener información detallada sobre un indicador seleccionado (Página 2)
@app.route('/get_indicator_info', methods=['POST'])
def get_indicator_info():
    indicator_name = request.json['indicator']
    indicator_row = df[df['Indicator'] == indicator_name].iloc[0]  # Obtener la primera fila coincidente

    if indicator_row is not None:
        return jsonify({
            "Rationale": indicator_row['Rationale'],
            "Formula": indicator_row['Formula'],
            "Source": indicator_row['Source']
        })
    return jsonify({"error": "Indicator not found"}), 404

# Route para procesar datos para la página 3 (Ranking)
@app.route('/process_data', methods=['POST', 'GET'])
def process_data():
    if request.method == 'GET':
        selected_category = list(categories.keys())[0]  # Mostrar la primera categoría por defecto
        return render_template('form_adj.html', 
                               categories=categories.keys(), 
                               selected_category=selected_category, 
                               categories_json=categories)

    # Si es POST, procesa los datos enviados
    selected_category = request.form['category']
    indicators_list = categories[selected_category]
    
    user_input_data = []
    for indicator in indicators_list:
        relevance = int(request.form.get(f'{indicator}_r', 3))
        data_availability = int(request.form.get(f'{indicator}_q', 3))
        data_quality = int(request.form.get(f'{indicator}_d', 3))
        policy_importance = int(request.form.get(f'{indicator}_p', 3))

        # Guardar en la base de datos
        indicator_data = IndicatorData(
            category=selected_category,
            indicator=indicator,
            relevance=relevance,
            data_availability=data_availability,
            data_quality=data_quality,
            policy_importance=policy_importance
        )
        db.session.add(indicator_data)
        db.session.commit()

        # Añadir a la matriz para calcular el ranking
        user_input_data.append([relevance, data_availability, data_quality, policy_importance])

    # Procesar los datos ingresados
    df_ranking = process_indicator_data(user_input_data, indicators_list)

# Nuevas rutas para las pestañas adicionales

# Ruta para la página de High Priority Indicators
@app.route('/high_priority_indicators')
def high_priority_indicators():
    # Aquí puedes personalizar los datos que deseas mostrar en esta página
    high_priority_data = categories.get("High Priority", [])  # Puedes cambiar esto para mostrar datos específicos
    return render_template('high_priority.html', indicators=high_priority_data)

# Ruta para la página de Method of Shortlisting
@app.route('/method')
def method():
    # Lee el contenido desde el archivo HTML
    method_file_path = os.path.join(app.root_path, 'static', 'method_content.html')
    with open(method_file_path, 'r', encoding='utf-8') as file:
        method_content = Markup(file.read())  # Markup permite que el HTML se renderice correctamente

    return render_template('method.html', method_content=method_content)

# Ruta para la página de Documentation (abrir archivos PDF o Word)
@app.route('/documentation')
def documentation():
    # Enviar archivos para ser descargados o visualizados
    # Aquí puedes agregar archivos reales para la documentación
    return render_template('documentation.html')


    # Devolver la tabla de ranking
    return render_template('form.html', 
                           categories=categories.keys(), 
                           selected_category=selected_category, 
                           categories_json=categories, 
                           ranking=df_ranking.to_html(classes='table table-striped'))

if __name__ == '__main__':
    app.run(debug=True)
