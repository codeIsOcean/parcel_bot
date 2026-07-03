import { defineStore } from 'pinia'
import { ref } from 'vue'
import { parcelsApi } from '@/api/parcels'

/**
 * Store посылок — список, создание, отслеживание.
 */
export const useParcelsStore = defineStore('parcels', () => {
  // Список моих посылок
  const myParcels = ref([])

  // Загрузка
  const loading = ref(false)

  // Ошибка
  const error = ref(null)

  /**
   * Загрузить мои посылки.
   */
  const fetchMyParcels = async (params = {}) => {
    loading.value = true
    error.value = null
    try {
      const data = await parcelsApi.getMyParcels(params)
      myParcels.value = data.items || data
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  /**
   * Создать новую посылку.
   */
  const createParcel = async (parcelData) => {
    const parcel = await parcelsApi.create(parcelData)
    // Добавляем в начало списка
    myParcels.value.unshift(parcel)
    return parcel
  }

  /**
   * Отменить посылку.
   */
  const cancelParcel = async (id) => {
    await parcelsApi.cancel(id)
    // Обновляем статус в локальном списке
    const parcel = myParcels.value.find(p => p.id === id)
    if (parcel) parcel.status = 'cancelled'
  }

  return {
    myParcels,
    loading,
    error,
    fetchMyParcels,
    createParcel,
    cancelParcel,
  }
})
