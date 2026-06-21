<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Asset, AskResponse } from './api'
import { getAssets, createAsset, deleteAsset, askQuestion } from './api'

const assets = ref<Asset[]>([])
const loading = ref(false)

const newTitle = ref('')
const newContent = ref('')
const newTags = ref('')
const showForm = ref(false)

const askQuery = ref('')
const asking = ref(false)
const answer = ref('')
const sources = ref<AskResponse['sources']>([])
const trace = ref<any>(null)
const showTrace = ref(false)

const loadAssets = async () => {
  loading.value = true
  try { assets.value = await getAssets() } finally { loading.value = false }
}

const handleCreate = async () => {
  if (!newTitle.value.trim() || !newContent.value.trim()) { ElMessage.warning('标题和内容必填'); return }
  await createAsset({ title: newTitle.value, content: newContent.value, tags: newTags.value.split(',').map(t => t.trim()).filter(Boolean) })
  newTitle.value = ''; newContent.value = ''; newTags.value = ''; showForm.value = false
  ElMessage.success('添加成功')
  loadAssets()
}

const handleDelete = async (id: number) => {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await deleteAsset(id)
  ElMessage.success('删除成功')
  loadAssets()
}

const handleAsk = async () => {
  if (!askQuery.value.trim()) { ElMessage.warning('请输入问题内容'); return }
  asking.value = true; answer.value = ''; sources.value = []; trace.value = null
  try {
    const res = await askQuestion(askQuery.value)
    answer.value = res.answer
    sources.value = res.sources
    trace.value = res.trace
  } catch (e: any) {
    ElMessage.error(e.message || '请求失败')
  } finally { asking.value = false }
}

onMounted(loadAssets)
</script>

<template>
  <div style="max-width: 1200px; margin: 0 auto; padding: 20px;">
    <h2>知识资产问答工作台</h2>

    <el-divider content-position="left">知识资产管理</el-divider>
    <el-button type="primary" @click="showForm = true" style="margin-bottom: 10px;">新增</el-button>
    <el-table :data="assets" v-loading="loading" border size="small">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="content" label="内容" show-overflow-tooltip />
      <el-table-column prop="tags" label="标签" width="200">
        <template #default="{row}">{{ row.tags.join(', ') }}</template>
      </el-table-column>
      <el-table-column label="操作" width="80">
        <template #default="{row}">
          <el-button type="danger" size="small" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showForm" title="新增知识资产" width="600px">
      <el-form label-width="80px">
        <el-form-item label="标题"><el-input v-model="newTitle" /></el-form-item>
        <el-form-item label="内容"><el-input v-model="newContent" type="textarea" :rows="4" /></el-form-item>
        <el-form-item label="标签"><el-input v-model="newTags" placeholder="逗号分隔" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showForm = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>

    <el-divider content-position="left">智能问答</el-divider>
    <el-input v-model="askQuery" placeholder="输入问题" style="width: 400px; margin-right: 10px;" @keyup.enter="handleAsk" />
    <el-button type="primary" @click="handleAsk" :loading="asking">提问</el-button>
    <div v-if="answer" style="margin-top: 15px; padding: 15px; border: 1px solid #eee; border-radius: 4px;">
      <p><b>回答：</b></p>
      <p style="white-space: pre-wrap;">{{ answer }}</p>
      <p style="margin-top: 10px;"><b>引用来源：</b></p>
      <ul style="margin: 5px 0;"><li v-for="s in sources" :key="s.id">{{ s.title }}</li></ul>
      <el-button size="small" @click="showTrace = !showTrace">Trace {{ showTrace ? '隐藏' : '显示' }}</el-button>
      <pre v-if="showTrace && trace" style="background: #f5f5f5; padding: 10px; font-size: 12px; overflow: auto; margin-top: 10px;">{{ JSON.stringify(trace, null, 2) }}</pre>
    </div>
  </div>
</template>
