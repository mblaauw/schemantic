# Overleg datateam, 14 mei (fictief)

Aanwezig: Sanne (data engineer), Ruben (analist), Femke (product owner).

- De kassasystemen in de 40 winkels sturen elke nacht een export naar de SFTP-server. Dat blijft voorlopig zo.
- De webshop stuurt bestellingen realtime als events naar Kafka.
- Een ingest-job in Airflow haalt de kassa-exports op en zet ze in de Bronze-laag van het lakehouse.
- Kafka-events gaan via een streaming-job (Flink) ook naar Bronze.
- dbt bouwt Silver en Gold. Gold heeft per domein een schema: verkoop, voorraad, klanten.
- Analisten gebruiken alleen Gold, via Power BI. Besluit: niemand bouwt rapporten op Silver.
- Besluit: alle pipelines staan in Git en gaan via CI naar productie; handmatige wijzigingen in productie zijn niet toegestaan.
- Open punt: blijven de nachtelijke kassa-exports, of moeten de kassa's ook events naar Kafka sturen?
- Ruben vraagt om een dagelijkse voorraadrapportage per winkel; die komt uit Gold.
