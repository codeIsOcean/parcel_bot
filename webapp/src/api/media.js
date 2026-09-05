import api from './client'

/**
 * API загрузки фотографий.
 */
export const mediaApi = {
  /**
   * Прикрепить фото к посылке на нужном этапе.
   * step: parcel | handover | delivery
   */
  attachToParcel: (parcelId, file, step = 'parcel') => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/media/parcels/${parcelId}/photos?step=${step}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  /**
   * Загрузить файл без привязки к посылке.
   */
  upload: (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/media/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
