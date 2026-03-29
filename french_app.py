# Routes pour le dictionnaire français-kabiyè
@app.route('/francais')
def accueil_francais():
    """Page d'accueil du dictionnaire français-kabiyè"""
    return render_template('formulaire_francais.html')

@app.route('/editer_francais/<int:mot_id>')
def editer_mot_francais(mot_id):
    """Page d'édition d'un mot français"""
    from database import MotFrancais
    
    session = get_session()
    try:
        mot = session.query(MotFrancais).filter(MotFrancais.id == mot_id).first()
        if not mot:
            return "Mot non trouvé", 404
        
        # Convertir les données JSON en listes pour le template
        mot_dict = {
            'id': mot.id,
            'mot_francais': mot.mot_francais,
            'variantes_orthographiques': ', '.join(json_to_list(mot.variantes_orthographiques)) if mot.variantes_orthographiques else '',
            'traduction_kabye': mot.traduction_kabye or '',
            'sens_multiple': '; '.join(json_to_list(mot.sens_multiple)) if mot.sens_multiple else '',
            'synonymes': ', '.join(json_to_list(mot.synonymes)) if mot.synonymes else '',
            'antonymes': ', '.join(json_to_list(mot.antonymes)) if mot.antonymes else '',
            'categorie_grammaticale': mot.categorie_grammaticale or '',
            'sous_categorie': mot.sous_categorie or '',
            'exemple_usage': mot.exemple_usage or '',
            'traduction_exemple': mot.traduction_exemple or '',
            'expressions_associees': json_to_list(mot.expressions_associees),
            'notes_usage': mot.notes_usage or '',
            'image_url': mot.image_url or '',
            'verifie_par': mot.verifie_par or '',
            'date_ajout': mot.date_ajout.strftime("%Y-%m-%d %H:%M:%S") if mot.date_ajout else '',
            'date_modification': mot.date_modification.strftime("%Y-%m-%d %H:%M:%S") if mot.date_modification else ''
        }
        
        return render_template('formulaire_francais.html', mot=mot_dict, edition=True)
    finally:
        session.close()

@app.route('/sauvegarder_francais', methods=['POST'])
def sauvegarder_mot_francais():
    from database import MotFrancais
    
    session = get_session()
    try:
        # Gérer les données form-data (avec fichier)
        if request.content_type.startswith('multipart/form-data'):
            data = request.form
            image_file = request.files.get('image')
        else:
            data = request.get_json()
            image_file = None
        
        # Validation
        if not data.get('mot_francais') or not data.get('traduction_kabye'):
            return jsonify({'success': False, 'error': 'Mot français et traduction kabiyè sont obligatoires'})
        
        # Vérifier si c'est une édition
        mot_id = data.get('mot_id')
        if mot_id:
            # MODE ÉDITION
            mot_id = int(mot_id)
            mot = session.query(MotFrancais).filter(MotFrancais.id == mot_id).first()
            
            if not mot:
                return jsonify({'success': False, 'error': 'Mot non trouvé'})
            
            # Vérifier si le nom a changé et s'il existe déjà
            if mot.mot_francais.lower() != data['mot_francais'].lower():
                mot_existe = session.query(MotFrancais).filter(
                    func.lower(MotFrancais.mot_francais) == data['mot_francais'].lower(),
                    MotFrancais.id != mot_id
                ).first()
                if mot_existe:
                    return jsonify({'success': False, 'error': 'Ce mot existe déjà dans le dictionnaire'})
            
            # Gérer l'image
            image_url = mot.image_url or ''
            supprimer_ancienne_image = data.get('supprimer_image') == 'true'
            
            if supprimer_ancienne_image and image_url:
                supprimer_image_cloudinary(image_url)
                image_url = ""
            
            if image_file and image_file.filename != '':
                if allowed_file(image_file.filename):
                    if image_url:
                        supprimer_image_cloudinary(image_url)
                    image_url = upload_image_cloudinary(image_file)
                    if not image_url:
                        return jsonify({'success': False, 'error': 'Erreur lors du téléchargement de l\'image'})
                else:
                    return jsonify({'success': False, 'error': 'Type de fichier non autorisé'})
        else:
            # MODE CRÉATION
            mot_existe = session.query(MotFrancais).filter(
                func.lower(MotFrancais.mot_francais) == data['mot_francais'].lower()
            ).first()
            
            if mot_existe:
                return jsonify({'success': False, 'error': 'Ce mot existe déjà dans le dictionnaire'})
            
            # Upload de l'image
            image_url = ""
            if image_file and image_file.filename != '':
                if allowed_file(image_file.filename):
                    image_url = upload_image_cloudinary(image_file)
                    if not image_url:
                        return jsonify({'success': False, 'error': 'Erreur lors du téléchargement de l\'image'})
                else:
                    return jsonify({'success': False, 'error': 'Type de fichier non autorisé'})
            
            # Créer un nouveau mot
            mot = MotFrancais()
        
        # Traiter les listes
        variantes = [v.strip() for v in data.get('variantes_orthographiques', '').split(',') if v.strip()]
        sens_multiple = [s.strip() for s in data.get('sens_multiple', '').split(';') if s.strip()]
        synonymes = [s.strip() for s in data.get('synonymes', '').split(',') if s.strip()]
        antonymes = [a.strip() for a in data.get('antonymes', '').split(',') if a.strip()]
        
        # Traiter les expressions associées
        expressions = []
        expressions_text = data.get('expressions_associees', '').strip()
        if expressions_text:
            for expr_line in expressions_text.split('\n'):
                if ':' in expr_line:
                    expr_parts = expr_line.split(':', 1)
                    expressions.append({
                        "expression": expr_parts[0].strip(),
                        "traduction": expr_parts[1].strip()
                    })
        
        # Mettre à jour les données du mot
        mot.mot_francais = data['mot_francais'].strip()
        mot.variantes_orthographiques = list_to_json(variantes)
        mot.traduction_kabye = data['traduction_kabye'].strip()
        mot.sens_multiple = list_to_json(sens_multiple)
        mot.synonymes = list_to_json(synonymes)
        mot.antonymes = list_to_json(antonymes)
        mot.categorie_grammaticale = data.get('categorie_grammaticale', '').strip()
        mot.sous_categorie = data.get('sous_categorie', '').strip()
        mot.exemple_usage = data.get('exemple_usage', '').strip()
        mot.traduction_exemple = data.get('traduction_exemple', '').strip()
        mot.expressions_associees = list_to_json(expressions)
        mot.notes_usage = data.get('notes_usage', '').strip()
        mot.image_url = image_url
        mot.verifie_par = data.get('verifie_par', 'Anonyme').strip()
        mot.date_modification = datetime.now()
        
        if not mot_id:
            mot.date_ajout = datetime.now()
            session.add(mot)
        
        session.commit()
        
        message = f'✅ Mot "{data["mot_francais"]}" sauvegardé avec succès !'
        if mot_id:
            message = f'✅ Mot "{data["mot_francais"]}" modifié avec succès !'
        
        return jsonify({
            'success': True, 
            'message': message,
            'image_url': image_url,
            'mot_id': mot.id
        })
            
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        session.close()

@app.route('/supprimer_francais/<int:mot_id>', methods=['POST'])
def supprimer_mot_francais(mot_id):
    from database import MotFrancais
    
    session = get_session()
    try:
        mot = session.query(MotFrancais).filter(MotFrancais.id == mot_id).first()
        
        if not mot:
            return jsonify({'success': False, 'error': 'Mot non trouvé'})
        
        nom_mot = mot.mot_francais
        
        if mot.image_url:
            supprimer_image_cloudinary(mot.image_url)
        
        session.delete(mot)
        session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'✅ Mot "{nom_mot}" supprimé avec succès !'
        })
            
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        session.close()

@app.route('/mots_francais')
def liste_mots_francais():
    """Afficher tous les mots français avec recherche multi-critères"""
    from database import MotFrancais
    
    session = get_session()
    try:
        terme_recherche = request.args.get('q', '').strip().lower()
        champ_recherche = request.args.get('champ', 'tous')
        initiale = request.args.get('initiale', '').upper()
        
        query = session.query(MotFrancais)
        
        if initiale and len(initiale) == 1:
            query = query.filter(MotFrancais.mot_francais.startswith(initiale))
        
        if terme_recherche:
            if champ_recherche in ['tous', 'francais']:
                query = query.filter(
                    or_(
                        MotFrancais.mot_francais.ilike(f'%{terme_recherche}%'),
                        MotFrancais.variantes_orthographiques.ilike(f'%{terme_recherche}%')
                    )
                )
            elif champ_recherche in ['tous', 'kabye']:
                query = query.filter(
                    or_(
                        MotFrancais.traduction_kabye.ilike(f'%{terme_recherche}%'),
                        MotFrancais.sens_multiple.ilike(f'%{terme_recherche}%')
                    )
                )
        
        mots = query.order_by(MotFrancais.date_modification.desc()).all()
        
        mots_affichage = []
        for mot in mots:
            mots_affichage.append({
                'id': mot.id,
                'mot_francais': mot.mot_francais,
                'traduction_kabye': mot.traduction_kabye,
                'exemple_usage': mot.exemple_usage,
                'verifie_par': mot.verifie_par,
                'categorie_grammaticale': mot.categorie_grammaticale,
                'date_modification': mot.date_modification.strftime("%Y-%m-%d %H:%M:%S") if mot.date_modification else '',
                'image_url': mot.image_url
            })
        
        return render_template('liste_mots_francais.html', 
                             mots=mots_affichage, 
                             terme_recherche=terme_recherche,
                             nombre_resultats=len(mots_affichage),
                             champ_recherche=champ_recherche,
                             initiale_recherche=initiale)
    finally:
        session.close()

@app.route('/api/mots_francais')
def api_mots_francais():
    """API pour récupérer les mots français en JSON"""
    from database import MotFrancais
    
    session = get_session()
    try:
        mots = session.query(MotFrancais).all()
        result = []
        for mot in mots:
            result.append({
                'id': mot.id,
                'mot_francais': mot.mot_francais,
                'variantes_orthographiques': json_to_list(mot.variantes_orthographiques),
                'traduction_kabye': mot.traduction_kabye,
                'sens_multiple': json_to_list(mot.sens_multiple),
                'synonymes': json_to_list(mot.synonymes),
                'antonymes': json_to_list(mot.antonymes),
                'categorie_grammaticale': mot.categorie_grammaticale,
                'sous_categorie': mot.sous_categorie,
                'exemple_usage': mot.exemple_usage,
                'traduction_exemple': mot.traduction_exemple,
                'expressions_associees': json_to_list(mot.expressions_associees),
                'notes_usage': mot.notes_usage,
                'image_url': mot.image_url,
                'verifie_par': mot.verifie_par,
                'date_ajout': mot.date_ajout.strftime("%Y-%m-%d %H:%M:%S") if mot.date_ajout else '',
                'date_modification': mot.date_modification.strftime("%Y-%m-%d %H:%M:%S") if mot.date_modification else ''
            })
        return jsonify(result)
    finally:
        session.close()