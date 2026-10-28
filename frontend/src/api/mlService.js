import api from './axios.js';

/** ML endpoints — powers the Model Insights page. */
export const mlService = {
  /** Current model metadata (accuracy, sample count, classes, etc). */
  modelInfo: async () => (await api.get('/ml/model-info')).data,

  /** All saved model versions (newest first). Enables a rollback UI. */
  versions: async () => (await api.get('/ml/versions')).data,

  /** Preview what the model would predict for a given description. */
  predict: async (description, txn_type = 'debit') =>
    (await api.post('/ml/predict', { description, txn_type })).data,

  /** Manually trigger a retrain. Returns the new model info. */
  retrain: async () => (await api.post('/ml/retrain')).data,

  /** How many corrections until auto-retrain fires? */
  correctionStatus: async () => (await api.get('/ml/correction-status')).data,

  /** Statistically unusual transactions (z-score outliers). */
  anomalies: async (month) => (await api.get('/ml/anomalies', { params: { month } })).data,

  /** Linear-trend projection of this month's total spending. */
  forecast: async () => (await api.get('/ml/forecast')).data,
};
