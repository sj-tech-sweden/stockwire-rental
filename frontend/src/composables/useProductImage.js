import { ref } from 'vue'
import { api } from '../boot/axios'

/**
 * Composable for loading a product image from the storage API.
 * Handles blob URL creation, caching, and cleanup.
 *
 * @param {Object} options
 * @param {number|null} options.productId - Reactive product ID to fetch image for
 * @returns {{ imageUrl: import('vue').Ref<string>, fetchImage: (id?: number|null) => Promise<void>, cleanup: () => void }}
 */
export function useProductImage({ productId } = {}) {
  const imageUrl = ref('')
  const currentRequestId = ref(0)

  async function fetchImage(targetProductId) {
    const id = targetProductId ?? productId?.value ?? null
    const requestId = ++currentRequestId.value

    if (imageUrl.value && imageUrl.value.startsWith('blob:')) {
      URL.revokeObjectURL(imageUrl.value)
    }
    imageUrl.value = ''

    if (!id) return

    try {
      const { data } = await api.get('/api/v1/storage/files', {
        params: { entity_type: 'product', entity_id: id, category: 'product-image' },
      })
      const files = Array.isArray(data) ? data : []
      if (!files.length) return

      const blobData = await api.get(files[0].download_url, { responseType: 'blob' }).then(r => r.data)

      if (requestId !== currentRequestId.value) return

      imageUrl.value = URL.createObjectURL(blobData)
    } catch {
      if (requestId === currentRequestId.value) {
        imageUrl.value = ''
      }
    }
  }

  function cleanup() {
    if (imageUrl.value && imageUrl.value.startsWith('blob:')) {
      URL.revokeObjectURL(imageUrl.value)
    }
    imageUrl.value = ''
  }

  return { imageUrl, fetchImage, cleanup }
}
