# Event Liklihood - Predicting if a user would like to listen to music

This project attempts to predict whether a user is interested in listening to music at current time t, given their past history. The project makes use of Scikit-Learn and Tensorflow.

The model makes usse of the LastFM 100k user [dataset](http://www.dtic.upf.edu/~ocelma/MusicRecommendationDataset/lastfm-1K.html) which was transformed into time-series data and stored in SQLite.

Methods applied were:
- Logistic regression
- Linear SVM Model
- RBF SVM Model
- RNN-LSTM

Shortcut to the final report is [here](https://github.com/BadrulAlom/EventPrediction/blob/master/0_Docs/report/latex/COMPGI99-Alom-Badrul.pdf)

- [1_codemodule folder](https://github.com/BadrulAlom/EventPrediction/tree/master/1_Codemodule) - Some common code
- [2_Settings](https://github.com/BadrulAlom/EventPrediction/tree/master/2_Settings) - Stores database and file paths
- [3_Data]() - Not in git as too large
- [4_DataProcessing](https://github.com/BadrulAlom/EventPrediction/tree/master/4_DataProcessing) - Transformation of raw data into time-series data
- [5_PreliminaryAnalysis](https://github.com/BadrulAlom/EventPrediction/tree/master/5_PreliminaryAnalysis) - Quick look at the raw and transformed data
- [6_MainModel](https://github.com/BadrulAlom/EventPrediction/tree/master/6_MainModel) - Main code




