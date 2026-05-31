import { api } from '../lib/client'
import type { KbDocument, KbUploadResponse } from '../lib/types'

/** Supported KB file extensions (mirrors app/rag/extract.SUPPORTED_EXTENSIONS). */
export const SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.csv', '.json']

export function listDocuments(): Promise<KbDocument[]> {
  return api.get<KbDocument[]>('/data/documents')
}

export function uploadFile(file: File): Promise<KbUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  return api.postForm<KbUploadResponse>('/data/upload', form)
}

export function ingestUrl(url: string): Promise<KbUploadResponse> {
  return api.post<KbUploadResponse>('/data/url', { url })
}

export function ingestFaq(
  question: string,
  answer: string,
): Promise<KbUploadResponse> {
  return api.post<KbUploadResponse>('/data/faq', { question, answer })
}
