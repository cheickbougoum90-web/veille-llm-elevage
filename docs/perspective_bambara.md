# Perspective : le bambara

Le bambara est hors du périmètre noté, mais le sourcing est fait et sert de conclusion au livrable. C'est un signal faible au sens du cours.

- Reconnaissance vocale : [benchmark bambara](https://www.arxiv.org/abs/2602.09785) et [modèles MALIBA-AI](https://huggingface.co/sudoping01/bambara-asr-v2). Des modèles basés sur Whisper gèrent le bambara et le mélange bambara français.
- Données : le corpus [Kunkado](https://arxiv.org/abs/2512.19400v1) rassemble environ 160 heures de radios maliennes.
- Synthèse vocale : le paquet [maliba-ai](https://pypi.org/project/maliba-ai/), pour un usage non commercial seulement.
- Première étape possible : un glossaire d'élevage de 50 à 100 termes validé par un locuteur, puis un test de traduction sur 20 à 30 phrases.
- Limites : qualité de traduction encore modeste (environ 10 % de BLEU dans la littérature) et licences non commerciales pour les meilleurs modèles.
