import { toast } from 'sonner'
import { errorMessage } from '@/lib/api'
import { t } from '@/lib/i18n'

/** Toast yordamchilari. O'chirish/bekor qilishda "Qaytarish" (undo) imkoni bilan. */
export const notify = {
  success: (message: string, description?: string) => toast.success(message, { description }),
  info: (message: string, description?: string) => toast.info(message, { description }),
  warning: (message: string, description?: string) => toast.warning(message, { description }),
  error: (message: string, error?: unknown) =>
    toast.error(message, { description: error === undefined ? undefined : errorMessage(error), duration: 8000 }),
  /** Amal bajarildi, foydalanuvchi 6 soniya ichida qaytarishi mumkin. */
  undoable: (message: string, onUndo: () => void | Promise<void>) =>
    toast(message, {
      duration: 6000,
      action: { label: t.common.undo, onClick: () => void onUndo() },
    }),
}
