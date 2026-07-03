import { defineStore } from 'pinia'
import { ref } from 'vue'
import { flightsApi } from '@/api/flights'

/**
 * Store рейсов — поиск попутчиков, публикация рейсов.
 */
export const useFlightsStore = defineStore('flights', () => {
  // Результаты поиска (список попутчиков)
  const searchResults = ref([])

  // Мои рейсы (для перевозчика)
  const myFlights = ref([])

  // Загрузка
  const loading = ref(false)

  // Ошибка
  const error = ref(null)

  /**
   * Поиск попутчиков по маршруту.
   */
  const searchFlights = async (params = {}) => {
    loading.value = true
    error.value = null
    try {
      const data = await flightsApi.search(params)
      searchResults.value = data.items || data
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  /**
   * Загрузить мои рейсы.
   */
  const fetchMyFlights = async () => {
    loading.value = true
    error.value = null
    try {
      const data = await flightsApi.getMyFlights()
      myFlights.value = data.items || data
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  /**
   * Опубликовать новый рейс.
   */
  const publishFlight = async (flightData) => {
    const flight = await flightsApi.create(flightData)
    myFlights.value.unshift(flight)
    return flight
  }

  return {
    searchResults,
    myFlights,
    loading,
    error,
    searchFlights,
    fetchMyFlights,
    publishFlight,
  }
})
