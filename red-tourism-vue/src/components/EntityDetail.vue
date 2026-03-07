<template>
  <div class="entity-detail">
    <div v-if="!entity" class="detail-empty">
      <el-empty description="点击图谱中的节点查看详情" />
    </div>

    <div v-else class="detail-content">
      <div class="detail-header">
        <h3>{{ entity.name }}</h3>
        <el-tag size="small">{{ entity.type }}</el-tag>
      </div>
      <el-divider />
      <div class="detail-props">
        <div v-for="(val, key) in entity.props" :key="key" class="prop-item">
          <span class="prop-label">{{ key }}：</span>
          <span class="prop-value">{{ val }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'EntityDetail',
  props: {
    entity: {
      type: Object,
      default: null
    }
  }
}
</script>

<style scoped>
.entity-detail {
  height: 100%;
  padding: 16px;
}

.detail-empty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.detail-header h3 {
  margin: 0;
  font-size: 16px;
}

.prop-item {
  margin-bottom: 8px;
  font-size: 13px;
}

.prop-label {
  color: #999;
  margin-right: 8px;
}

.prop-value {
  color: #333;
}
</style>