from flask import Flask, render_template, jsonify, request, send_file, send_from_directory, url_for
from markupsafe import Markup
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import numpy as np
import pandas as pd
import os
import io
import logging


app = Flask(__name__)

@app.route('/projects/mimunido/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.path.join(app.root_path, 'projects/mimunido/static'), filename)

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

class SelectedIndicators(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    indicator = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# Inicializar la base de datos
with app.app_context():
    #db.drop_all()
    db.create_all()

# Cargar el archivo Excel una sola vez
#csv_file_path = os.path.join(os.getcwd(), 'indicators.xlsx')
csv_file_path = os.path.join(os.path.dirname(__file__), 'indicators.xlsx')
if os.path.exists(csv_file_path):
    df = pd.read_excel(csv_file_path)
else:
    raise FileNotFoundError(f"File not found: {csv_file_path}")

# Agrupar los indicadores por categoría
categories = df.groupby('Category')['Indicator'].apply(list).to_dict()

sector_categories = df.groupby(['Sector', 'Category'])['Indicator'].apply(list).to_dict()

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

@app.route('/projects/mimunido/export_data')
def export_data():
    # Obtener todos los datos de la base de datos
    data = IndicatorData.query.all()
    highlighted = SelectedIndicators.query.all()

    # Convertir los datos de IndicatorData en un DataFrame de pandas
    rows = [{
        'Category': d.category,
        'Indicator': d.indicator,
        'Relevance': d.relevance,
        'Data Availability': d.data_availability,
        'Data Quality': d.data_quality,
        'Policy Importance': d.policy_importance,
        'Timestamp': d.timestamp
    } for d in data]
    df_data = pd.DataFrame(rows)

    # Convertir los datos de SelectedIndicators en un DataFrame de pandas
    highlighted_rows = [{
        'Indicator': h.indicator,
        'Score': h.score
    } for h in highlighted]
    df_highlighted = pd.DataFrame(highlighted_rows)

    # Añadir la columna 'Ranking' a df_data, basada en df_highlighted
    if not df_highlighted.empty:
        df_data['Ranking'] = df_data['Indicator'].map(
            df_highlighted.set_index('Indicator')['Score']
        )
    else:
        df_data['Ranking'] = None

    # Crear un archivo CSV en memoria
    output = io.BytesIO()
    df_data.to_csv(output, index=False)
    output.seek(0)

    # Enviar el archivo CSV para su descarga
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='indicator_data_with_ranking.csv')

    
@app.route('/projects/mimunido/')
def home():
    selected_indicators = [indicator.indicator for indicator in SelectedIndicators.query.all()]
    selected_indicators = selected_indicators or []
    image_url = url_for('serve_static', filename='image1.jpg')
    return render_template(
        'index_indi_adj_up.html', 
        categories=categories, 
        show_presentation=True, 
        selected_indicators=selected_indicators,
        image_url=image_url
    )


@app.route('/projects/mimunido/indicator_list', methods=['GET'])
def indicators_list():
    sector = request.args.get('sector', 'Manufacturing')
    print(f"Sector recibido: {sector}")  # Depuración: imprime el sector recibido

    # Filtrar las categorías según el sector
    filtered_categories = {
        category: indicators
        for (sec, category), indicators in sector_categories.items()
        if sec == sector
    }
    print(f"Categorías filtradas: {filtered_categories}")  # Depuración: imprime las categorías filtradas

    # Obtener indicadores seleccionados de la base de datos
    selected_indicators = [indicator.indicator for indicator in SelectedIndicators.query.all()] or []
    print(f"Indicadores seleccionados: {selected_indicators}")  # Depuración: imprime los indicadores seleccionados

    return render_template(
        'index_indi_adj_up.html',
        categories=filtered_categories,
        sector=sector,
        selected_indicators=selected_indicators,
        show_presentation=False,
    )


@app.route('/projects/mimunido/indicators', methods=['GET'])
def get_indicators():
    sector = request.args.get('sector', 'Manufacturing')  # Valor por defecto
    filtered_categories = {
        category: indicators
        for (sec, category), indicators in sector_categories.items()
        if sec == sector
    }
    return jsonify(filtered_categories)



# Route para obtener información detallada sobre un indicador seleccionado (Página 2)
#@app.route('/projects/mimunido/get_indicator_info', methods=['POST'])

# Route para obtener información detallada sobre un indicador seleccionado (Página 2)
@app.route('/projects/mimunido/get_indicator_info', methods=['POST'])
def get_indicator_info():
    sector = request.json.get('sector', 'Manufacturing')  # Default to Manufacturing
    indicator_name = request.json['indicator']
    print(f"Request recibido: Sector = {sector}, Indicator = {indicator_name}")

    try:
        # Filtrar por sector e indicador
        indicator_row = df[(df['Sector'] == sector) & (df['Indicator'] == indicator_name)].iloc[0]
        print("Datos filtrados para tabla de detalles:", indicator_row)

        # Crear estructura de datos para la tabla
        return jsonify({
            "Indicator code": indicator_row.get('Code', 'N/A'),
            "Dimension": indicator_row.get('Category', 'N/A'),
            "Indicator name": indicator_row.get('Indicator', 'N/A'),
            "Description": indicator_row.get('Rationale', 'N/A'),
            "Directionality": indicator_row.get('Directionality', 'N/A'),
            "Calculation methodology/Formula": indicator_row.get('Formula', 'N/A'),
            "Disaggregation": indicator_row.get('Disaggregation', 'N/A'),
            "Units": indicator_row.get('Units', 'N/A'),
            "Reporting frequency": indicator_row.get('Reporting frequency', 'N/A'),
            "Date of data availability": indicator_row.get('Date of data availability', 'N/A'),
            "Data source": indicator_row.get('Source', 'N/A'),
            "Data steward": indicator_row.get('Data steward', 'N/A')
        })

    except IndexError:
        print("No se encontraron datos para el filtro aplicado.")  
        return jsonify({"error": "Indicator not found"}), 404


'''
def get_indicator_info():
    sector = request.json.get('sector', 'Manufacturing')  # Default to Manufacturing
    indicator_name = request.json['indicator']
    #indicator_row = df[df['Indicator'] == indicator_name].iloc[0]  # Obtener la primera fila coincidente
    indicator_row = df[(df['Sector'] == sector) & (df['Indicator'] == indicator_name)].iloc[0]

    if indicator_row is not None:
        return jsonify({
            "Rationale": indicator_row['Rationale'],
            "Formula": indicator_row['Formula'],
            "Source": indicator_row['Source']
        })
    return jsonify({"error": "Indicator not found"}), 404
'''

# Route para procesar datos para la página 3 (Ranking)

@app.route('/projects/mimunido/process_data', methods=['POST', 'GET'])
def process_data():

    # Obtener el sector seleccionado de la URL (Manufacturing por defecto)
    sector = request.args.get('sector', 'Manufacturing')

   
    filtered_categories = {
        category: indicators
        for (sec, category), indicators in sector_categories.items()
        if sec == sector
    }

    print(f"Sector seleccionado: {sector}")
    print(f"Categorías filtradas para el sector {sector}: {filtered_categories}")

     # Si no hay categorías para el sector, maneja el caso vacío
    if not filtered_categories:
        return render_template(
            'form_adj_up.html',
            categories=[],
            selected_category=None,
            categories_json={}
        )

    if request.method == 'GET':
        selected_category = list(filtered_categories.keys())[0]  # Display the first category by default
        return render_template('form_adj_up.html', 
                               categories=filtered_categories.keys(), 
                               selected_category=selected_category, 
                               categories_json=filtered_categories,
                               sector=sector)


    elif request.method == 'POST':

        # Obtener el sector seleccionado del formulario
        sector = request.form['sector']  # Esto asegura que tomas el sector del formulario POST
        print(f"Sector recibido en el POST: {sector}")

        # Refiltrar categorías basadas en el sector
        filtered_categories = {
            category: indicators
            for (sec, category), indicators in sector_categories.items()
            if sec == sector
        }


        # Process POST data
        selected_category = request.form['category']
        indicators_list = filtered_categories[selected_category]
        
        user_input_data = []
        for indicator in indicators_list:
            relevance = int(request.form.get(f'{indicator}_r', 3))
            data_availability = int(request.form.get(f'{indicator}_q', 3))
            data_quality = int(request.form.get(f'{indicator}_d', 3))
            policy_importance = int(request.form.get(f'{indicator}_p', 3))

            # Save data to database
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

            # Add to the list for ranking calculation
            user_input_data.append([relevance, data_availability, data_quality, policy_importance])

        # Process the data to get ranking
        df_ranking = process_indicator_data(user_input_data, indicators_list)

        # Guardar los dos indicadores con mayor puntaje
        top_indicators = df_ranking.nlargest(2, 'Score')

        # Limpiar la tabla antes de agregar los nuevos indicadores
        SelectedIndicators.query.delete()

        # Agregar los nuevos indicadores seleccionados
        for _, row in top_indicators.iterrows():
            selected_indicator = SelectedIndicators(
                indicator=row['Indicator'],
                score=row['Score']
            )
            db.session.add(selected_indicator)

        db.session.commit()


        # Render the template with the ranking results
        return render_template('form_adj_up.html', 
                               categories=filtered_categories.keys(),
                               selected_category=selected_category,
                               categories_json=filtered_categories,
                               ranking=df_ranking.to_html())  # Pass the ranking as HTML

# Nuevas rutas para las pestañas adicionales

# Ruta para la página de High Priority Indicators
@app.route('/projects/mimunido/high_priority_indicators')
def high_priority_indicators():
    # Aquí puedes personalizar los datos que deseas mostrar en esta página
    high_priority_data = categories.get("High Priority", [])  # Puedes cambiar esto para mostrar datos específicos
    return render_template('high_priority_up.html', indicators=high_priority_data)

# Ruta para la página de Method of Shortlisting
@app.route('/projects/mimunido/method')
def method():
    # Lee el contenido desde el archivo HTML
    method_file_path = os.path.join(app.root_path, 'static', 'method_content.html')
    with open(method_file_path, 'r', encoding='utf-8') as file:
        method_content = Markup(file.read())  # Markup permite que el HTML se renderice correctamente

    return render_template('method_up.html', method_content=method_content)

# Ruta para la página de Documentation (abrir archivos PDF o Word)
@app.route('/projects/mimunido/documentation')
def documentation():
    # Enviar archivos para ser descargados o visualizados
    # Aquí puedes agregar archivos reales para la documentación
    return render_template('documentation_up.html')

@app.route('/projects/mimunido/contact')
def contact():
    # Page of contact
    return render_template('contact.html')

    # Devolver la tabla de ranking
    return render_template('form.html', 
                           categories=categories.keys(), 
                           selected_category=selected_category, 
                           categories_json=categories, 
                           ranking=df_ranking.to_html(classes='table table-striped'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

