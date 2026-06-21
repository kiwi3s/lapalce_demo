import axios from 'axios'

const request = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000
})

export interface Asset { id: number; title: string; content: string; tags: string[]; created_at: string }
export interface SearchResult { id: number; title: string; content: string; tags: string[]; score: number }
export interface AskResponse { answer: string; sources: {id: number; title: string; content: string}[]; trace: any }

export const getAssets = () => request.get<Asset[]>('/assets').then(r => r.data)
export const createAsset = (data: {title: string; content: string; tags: string[]}) => request.post('/assets', data).then(r => r.data)
export const deleteAsset = (id: number) => request.delete(`/assets/${id}`).then(r => r.data)
export const searchAssets = (q: string, top_n?: number) => request.get<SearchResult[]>('/search', {params: {q, top_n}}).then(r => r.data)
export const askQuestion = (query: string) => request.post<AskResponse>('/ask', {query}).then(r => r.data)
