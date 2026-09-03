<template>
  <div class="lib-root">
    <!-- ── Header ── -->
    <div class="lib-head">
      <div>
        <h1 class="lib-title">LoRA 资源库</h1>
        <p class="lib-sub">管理本地权重、来源目录、触发词映射与 Civitai 元数据。</p>
      </div>
      <div class="lib-actions">
        <button type="button" class="btn-tonal" @click="openSourceDialog">
          <span class="mdi mdi-folder-search-outline" />扫描来源
        </button>
        <button type="button" class="btn-primary" @click="openCreateDialog">
          <span class="mdi mdi-plus" />添加 LoRA
        </button>
      </div>
    </div>

    <!-- ── M3 Expressive Filter Bar（外层 24 圆角 tonal 面，内嵌 16 圆角搜索） ── -->
    <div class="filter-bar">
      <div class="search-field">
        <span class="mdi mdi-magnify search-icon" />
        <input
          v-model="searchQuery"
          class="search-input"
          placeholder="搜索 LoRA 名称或触发词"
        />
        <button v-if="searchQuery" type="button" class="search-clear" @click="searchQuery = ''">
          <span class="mdi mdi-close" />
        </button>
      </div>
      <BulkSelectionBar
        :selected-count="bulkSel.selectedCount"
        :is-all-selected="bulkSel.isAllSelected"
        @toggle-all="bulkSel.toggleAll()"
        @delete="openBulkDelete"
      />
      <button
        v-if="bulkSel.selectedCount > 0"
        type="button"
        class="btn-primary sm"
        :disabled="metaBusy"
        @click="openBulkMetadata"
      >
        <span class="mdi mdi-cloud-sync-outline" />补全所选 Metadata
      </button>
      <button
        v-else
        type="button"
        class="btn-tonal sm"
        :disabled="metaBusy || filteredLoras.length === 0"
        @click="refreshCurrentFilter"
      >
        <span class="mdi mdi-cloud-sync-outline" />补全当前结果
      </button>
      <div class="filter-side">
        <div class="view-toggle" role="tablist">
          <button
            type="button"
            :class="['vt-btn', { on: viewMode === 'card' }]"
            :title="'卡片视图'"
            @click="setViewMode('card')"
          >
            <span class="mdi mdi-view-grid-outline" />
          </button>
          <button
            type="button"
            :class="['vt-btn', { on: viewMode === 'list' }]"
            :title="'列表视图'"
            @click="setViewMode('list')"
          >
            <span class="mdi mdi-format-list-bulleted" />
          </button>
        </div>
        <button
          type="button"
          :class="['fav-btn', { on: onlyFavorites }]"
          @click="onlyFavorites = !onlyFavorites"
        >
          <span class="mdi" :class="onlyFavorites ? 'mdi-star' : 'mdi-star-outline'" />
          仅看收藏
        </button>
        <span class="count-mono mono">{{ filteredLoras.length }} 个模型</span>
      </div>
    </div>

    <!-- ── Empty ── -->
    <div v-if="filteredLoras.length === 0" class="lib-empty">
      <div class="lib-empty-icon"><span class="mdi mdi-toy-brick-outline" /></div>
      <p>暂无 LoRA 记录</p>
      <p class="lib-empty-hint">点击「扫描来源」添加本地目录并选择导入，或手动添加。</p>
    </div>

    <!-- ══════════ CARD VIEW（浏览模式，有封面；绝不显示本地绝对路径） ══════════ -->
    <div v-else-if="viewMode === 'card'" class="lora-cards">
      <div
        v-for="lora in filteredLoras"
        :key="lora.id"
        :class="['lora-card', { selected: bulkSel.isSelected(lora.id) }]"
      >
        <!-- Cover region -->
        <div v-if="!lora.cover_hidden" class="card-cover">
          <label class="head-check card-check">
            <input type="checkbox" :checked="bulkSel.isSelected(lora.id)" @change="bulkSel.toggleOne(lora.id)" />
          </label>
          <button
            type="button"
            :class="['fav-star', { on: lora.is_favorite }]"
            :title="lora.is_favorite ? '取消收藏' : '收藏'"
            @click="loraStore.toggleFavorite(lora)"
          >
            <span class="mdi" :class="lora.is_favorite ? 'mdi-star' : 'mdi-star-outline'" />
          </button>
          <img
            v-if="coverSrc(lora)"
            :src="coverSrc(lora)"
            :alt="lora.name"
            loading="lazy"
            class="cover-img"
            @error="onCoverError(lora)"
          />
          <div v-else class="cover-empty">
            <span class="mdi mdi-image-off-outline" />
            <span>暂无封面</span>
          </div>
        </div>

        <!-- Card body -->
        <div class="card-body">
          <div class="card-title-row">
            <span class="card-name" :title="lora.name">{{ lora.name }}</span>
            <span v-if="lora.is_favorite" class="mdi mdi-star card-fav-mini" />
          </div>
          <div v-if="lora.remote_model_name" class="card-remote-name" :title="lora.remote_model_name">
            {{ lora.remote_model_name }}
          </div>
          <div v-if="lora.remote_version_name || lora.remote_base_model" class="card-version">
            {{ lora.remote_version_name || '—' }}<template v-if="lora.remote_base_model"> · {{ lora.remote_base_model }}</template>
          </div>

          <div class="card-trigger">
            <span v-if="lora.trigger_words" class="mono">{{ lora.trigger_words }}</span>
            <span v-else-if="remoteTriggerText(lora)" class="mono" :title="remoteTriggerText(lora)">
              <span class="tw-src">Civitai</span>{{ remoteTriggerText(lora) }}
            </span>
            <span v-else class="none-hint">无触发词</span>
          </div>

          <div class="card-meta-row">
            <span class="mono weight" title="本地默认权重">{{ lora.default_strength.toFixed(2) }}</span>
            <span
              v-if="lora.remote_recommended_strength != null"
              class="mono rec-weight"
              title="Civitai 推荐权重（不会自动覆盖本地）"
            >Civitai {{ lora.remote_recommended_strength.toFixed(2) }}</span>
            <span :class="['meta-badge', metaStatusClass(lora)]">{{ metaStatusText(lora) }}</span>
            <span :class="['status-badge', lora.is_valid_file ? 'ok' : 'bad']">
              <span class="dot" />{{ lora.is_valid_file ? '就绪' : '未识别' }}
            </span>
          </div>

          <div class="card-actions">
            <button type="button" class="op-btn" title="编辑" @click="openEditDialog(lora)">
              <span class="mdi mdi-pencil-outline" />编辑
            </button>
            <button
              type="button"
              class="op-btn"
              title="刷新 Civitai 信息"
              :disabled="metaBusy"
              @click="refreshOne(lora)"
            >
              <span class="mdi" :class="refreshingIds.has(lora.id) ? 'mdi-loading mdi-spin' : 'mdi-refresh'" />刷新
            </button>
            <button
              v-if="lora.remote_model_id && lora.metadata_host"
              type="button"
              class="op-btn external"
              title="在 Civitai 打开"
              @click="openCivitai(lora)"
            >
              <span class="mdi mdi-open-in-new" />
            </button>
            <button type="button" class="op-btn danger" title="删除" @click="askDeleteLora(lora)">
              <span class="mdi mdi-delete-outline" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════ LIST VIEW（管理模式，无封面；无本地绝对路径/文件名大列） ══════════ -->
    <div v-else class="lora-list">
      <div class="lora-head">
        <span class="cell col-check">
          <label class="head-check">
            <input type="checkbox" :checked="bulkSel.isAllSelected" @change="bulkSel.toggleAll()" />
          </label>
        </span>
        <span class="cell col-fav">收藏</span>
        <span class="cell col-name">名称 / 分类</span>
        <span class="cell col-trigger">触发词</span>
        <span class="cell col-weight">权重</span>
        <span class="cell col-base">Base Model</span>
        <span class="cell col-meta">Metadata</span>
        <span class="cell col-status">ComfyUI</span>
        <span class="cell col-ops">操作</span>
      </div>
      <div v-for="lora in filteredLoras" :key="lora.id" class="lora-row">
        <div class="cell col-check">
          <label class="head-check">
            <input type="checkbox" :checked="bulkSel.isSelected(lora.id)" @change="bulkSel.toggleOne(lora.id)" />
          </label>
        </div>
        <div class="cell col-fav">
          <button
            type="button"
            :class="['fav-star', { on: lora.is_favorite }]"
            :title="lora.is_favorite ? '取消收藏' : '收藏'"
            @click="loraStore.toggleFavorite(lora)"
          >
            <span class="mdi" :class="lora.is_favorite ? 'mdi-star' : 'mdi-star-outline'" />
          </button>
        </div>
        <div class="cell col-name">
          <div class="name-line">
            <span class="lora-name" :title="lora.name">{{ lora.name }}</span>
            <span class="cat-pill">{{ lora.category || '通用' }}</span>
          </div>
        </div>
        <div class="cell col-trigger">
          <span v-if="lora.trigger_words" class="mono ellipsis trigger" :title="lora.trigger_words">{{ lora.trigger_words }}</span>
          <span
            v-else-if="remoteTriggerText(lora)"
            class="mono ellipsis trigger remote"
            :title="'Civitai 推荐：' + remoteTriggerText(lora)"
          ><span class="tw-src">Civitai</span>{{ remoteTriggerText(lora) }}</span>
          <span v-else class="none-hint">无触发词</span>
        </div>
        <div class="cell col-weight">
          <div class="weight-cell">
            <span class="mono weight">{{ lora.default_strength.toFixed(2) }}</span>
            <span
              v-if="lora.remote_recommended_strength != null"
              class="mono rec-mini"
              :title="'Civitai 推荐权重 ' + lora.remote_recommended_strength.toFixed(2)"
            >↳ {{ lora.remote_recommended_strength.toFixed(2) }}</span>
          </div>
        </div>
        <div class="cell col-base">
          <span v-if="lora.remote_base_model" class="ellipsis">{{ lora.remote_base_model }}</span>
          <span v-else class="none-hint">—</span>
        </div>
        <div class="cell col-meta">
          <span :class="['meta-badge', metaStatusClass(lora)]">{{ metaStatusText(lora) }}</span>
        </div>
        <div class="cell col-status">
          <span :class="['status-badge', lora.is_valid_file ? 'ok' : 'bad']">
            <span class="dot" />{{ lora.is_valid_file ? '就绪' : '未识别' }}
          </span>
        </div>
        <div class="cell col-ops">
          <button type="button" class="op-btn" title="编辑" @click="openEditDialog(lora)">
            <span class="mdi mdi-pencil-outline" />
          </button>
          <button
            type="button"
            class="op-btn"
            title="刷新 Civitai 信息"
            :disabled="metaBusy"
            @click="refreshOne(lora)"
          >
            <span class="mdi" :class="refreshingIds.has(lora.id) ? 'mdi-loading mdi-spin' : 'mdi-refresh'" />
          </button>
          <button
            v-if="lora.remote_model_id && lora.metadata_host"
            type="button"
            class="op-btn external"
            title="在 Civitai 打开"
            @click="openCivitai(lora)"
          >
            <span class="mdi mdi-open-in-new" />
          </button>
          <button type="button" class="op-btn danger" title="删除" @click="askDeleteLora(lora)">
            <span class="mdi mdi-delete-outline" />
          </button>
        </div>
      </div>
    </div>

    <!-- ══════════ 来源管理 Dialog（唯一展示目录地址的地方，spec §52） ══════════ -->
    <v-dialog v-model="sourceDialog" max-width="640px">
      <div class="m3-dialog">
        <div class="dialog-head">
          <span class="dialog-title">LoRA 来源管理</span>
          <button type="button" class="dialog-close" @click="sourceDialog = false">
            <span class="mdi mdi-close" />
          </button>
        </div>
        <p class="dialog-hint">扫描不会直接修改 LoRA 库；勾选预览后再「导入所选」。</p>

        <!-- 添加来源 -->
        <div class="add-source">
          <input
            v-model="newSourcePath"
            class="path-input mono"
            placeholder="目录路径，如 D:\ComfyUI\models\loras\Anima"
            @input="resolvePreview"
            @keyup.enter="addSource"
          />
          <label class="rec-check">
            <input v-model="newSourceRecursive" type="checkbox" />
            <span class="rec-box"><span v-if="newSourceRecursive" class="mdi mdi-check" /></span>
            递归子目录
          </label>
          <button type="button" class="btn-primary sm" :disabled="!newSourcePath.trim() || addingSource" @click="addSource">
            {{ addingSource ? '添加中…' : '添加来源' }}
          </button>
        </div>
        <p v-if="sourceError" class="form-error">{{ sourceError }}</p>
        <p v-if="newSourceResolved" class="path-preview">
          <span class="pv-label">实际解析路径</span>
          <span class="mono pv-path">{{ newSourceResolved }}</span>
        </p>
        <p v-if="resolveStatus && resolveStatus.ok" class="path-preview">
          <span class="pv-dot" /> 可访问 · {{ resolveStatus.count }} 个候选文件
        </p>
        <p v-else-if="resolveStatus && !resolveStatus.ok && resolveStatus.error" class="path-preview">
          <span class="pv-dot bad" /> {{ resolveStatus.error }}
        </p>

        <!-- 来源列表 -->
        <div class="source-list">
          <div v-for="s in loraStore.sources" :key="s.id" class="source-row">
            <span :class="['dot', s.exists && s.readable ? 'ok' : 'bad']" />
            <div class="source-main">
              <span class="mono src-display ellipsis" :title="s.display_path">{{ s.display_path }}</span>
              <span v-if="s.resolved_path !== s.display_path" class="mono src-resolved ellipsis" :title="s.resolved_path">{{ s.resolved_path }}</span>
              <span v-else-if="!s.exists" class="src-invalid">{{ s.error || '路径不可访问' }}</span>
            </div>
            <div class="source-ops">
              <button
                type="button"
                :class="['mini-switch', { on: s.enabled }]"
                :title="s.enabled ? '停用' : '启用'"
                @click="loraStore.updateSource(s.id, { enabled: !s.enabled })"
              >
                <span class="knob" />
              </button>
              <button
                type="button"
                :class="['mini-chip', { on: s.recursive }]"
                title="递归子目录"
                @click="loraStore.updateSource(s.id, { recursive: !s.recursive })"
              >
                递归
              </button>
              <button type="button" class="op-btn" title="扫描" :disabled="!s.enabled" @click="runScan(s)">
                <span class="mdi mdi-scan-helper" />
              </button>
              <button type="button" class="op-btn danger" title="删除来源（不影响已导入 LoRA）" @click="askDeleteSource(s)">
                <span class="mdi mdi-delete-outline" />
              </button>
            </div>
          </div>
          <div v-if="loraStore.sources.length === 0" class="src-empty">还没有来源目录</div>
        </div>

        <div class="dialog-foot">
          <button type="button" class="btn-tonal" @click="sourceDialog = false">关闭</button>
        </div>
      </div>
    </v-dialog>

    <!-- ══════════ 扫描预览 Dialog ══════════ -->
    <v-dialog v-model="scanDialog" max-width="860px">
      <div class="m3-dialog">
        <div class="dialog-head">
          <span class="dialog-title">扫描预览 · 选择导入</span>
          <button type="button" class="dialog-close" @click="scanDialog = false">
            <span class="mdi mdi-close" />
          </button>
        </div>
        <div v-if="scanResult" class="scan-body">
          <div class="scan-summary">
            <span class="sum-item"><b>{{ scanResult.summary.total }}</b>发现</span>
            <span class="sum-item primary"><b>{{ scanResult.summary.new }}</b>新增</span>
            <span class="sum-item muted"><b>{{ scanResult.summary.already_imported }}</b>已存在</span>
            <span :class="['sum-item', scanResult.summary.comfy_unrecognized > 0 ? 'warn' : 'muted']">
              <b>{{ scanResult.summary.comfy_unrecognized }}</b>ComfyUI 未识别
            </span>
            <span :class="['sum-item', scanResult.summary.basename_conflicts > 0 ? 'err' : 'muted']">
              <b>{{ scanResult.summary.basename_conflicts }}</b>重名冲突
            </span>
            <span v-if="!scanResult.summary.comfy_available" class="sum-item warn">ComfyUI 离线</span>
          </div>

          <div class="scan-toolbar">
            <button type="button" class="btn-tonal sm" @click="selectAllNew">全选新增</button>
            <button type="button" class="btn-ghost sm" @click="clearSelection">取消全选</button>
            <span class="scan-path mono ellipsis">{{ scanResult.source.display_path }}</span>
          </div>

          <div class="cand-list">
            <div class="cand-head">
              <span class="cell c-check" />
              <span class="cell c-name">文件</span>
              <span class="cell c-flag">状态</span>
            </div>
            <div
              v-for="c in scanResult.candidates"
              :key="c.full_path"
              :class="['cand-row', { disabled: c.exists_in_db }]"
            >
              <span class="cell c-check">
                <button
                  type="button"
                  :class="['row-check', { on: isSelected(c) }]"
                  :disabled="c.exists_in_db"
                  @click="toggleCandidate(c)"
                >
                  <span v-if="isSelected(c)" class="mdi mdi-check" />
                </button>
              </span>
              <span class="cell c-name">
                <span class="cand-name ellipsis">{{ c.name_hint }}</span>
                <span class="mono cand-path ellipsis" :title="c.relative_path">{{ c.relative_path }}</span>
              </span>
              <span class="cell c-flag">
                <span v-if="c.exists_in_db" class="flag done">已导入</span>
                <template v-else>
                  <span v-if="c.basename_conflict" class="flag err" title="多来源存在同名文件，导入后仍以完整相对路径区分">重名</span>
                  <span v-if="!c.comfy_recognized" class="flag warn" title="文件存在 · ComfyUI 未识别">文件存在 · ComfyUI 未识别</span>
                  <span v-if="c.comfy_recognized && !c.basename_conflict" class="flag ok">可导入</span>
                </template>
              </span>
            </div>
            <div v-if="scanResult.candidates.length === 0" class="src-empty">该目录下未发现 LoRA 权重文件</div>
          </div>
        </div>

        <div class="dialog-foot">
          <span class="foot-hint">已选 {{ selectedCandidates.length }} 项</span>
          <button type="button" class="btn-tonal" @click="scanDialog = false">取消</button>
          <button
            type="button"
            class="btn-primary"
            :disabled="selectedCandidates.length === 0 || importing"
            @click="doImport"
          >
            {{ importing ? '导入中…' : `导入所选（${selectedCandidates.length}）` }}
          </button>
        </div>
      </div>
    </v-dialog>

    <!-- ══════════ LoRA 创建/编辑 Dialog（本地 / 远端 / 技术 三区） ══════════ -->
    <v-dialog v-model="loraDialog" max-width="640px">
      <div class="m3-dialog">
        <div class="dialog-head">
          <span class="dialog-title">{{ isEdit ? '编辑 LoRA 设定' : '添加 LoRA' }}</span>
          <button type="button" class="dialog-close" @click="loraDialog = false">
            <span class="mdi mdi-close" />
          </button>
        </div>

        <div class="edit-sections">
          <!-- 本地信息 -->
          <div class="edit-section">
            <div class="edit-sec-title">本地信息</div>
            <div class="form-body">
              <label class="field">
                <span class="field-label">显示名称</span>
                <input v-model="form.name" class="field-input" placeholder="如: Water Dress" />
              </label>
              <label class="field">
                <span class="field-label">描述</span>
                <textarea v-model="form.description" class="field-input" rows="2" placeholder="本地备注（不会被远端刷新覆盖）" />
              </label>
              <label class="field">
                <span class="field-label">触发词 Trigger Words（英文逗号分隔）</span>
                <textarea v-model="form.trigger_words" class="field-input mono" rows="2" placeholder="如: water_dress, flowing_water" />
              </label>
              <label class="field">
                <span class="field-label">分类</span>
                <input v-model="form.category" class="field-input" />
              </label>
              <div class="strength-field">
                <span class="field-label">默认权重 <b class="mono">{{ form.default_strength.toFixed(2) }}</b></span>
                <div class="mini-slider" @pointerdown="onStrengthDown">
                  <div class="ms-track">
                    <div class="ms-fill" :style="{ width: strengthPct + '%' }" />
                    <div class="ms-thumb" :style="{ left: strengthPct + '%' }" />
                  </div>
                </div>
              </div>
              <div class="d-flex gap-3 align-center pt-2">
                <label class="edit-check">
                  <input v-model="form.is_favorite" type="checkbox" />
                  <span class="check-label">收藏</span>
                </label>
                <label class="edit-check">
                  <input v-model="form.cover_hidden" type="checkbox" />
                  <span class="check-label">隐藏封面（卡片视图收起封面区）</span>
                </label>
              </div>
            </div>
          </div>

          <!-- 远端信息（read-only） -->
          <div v-if="isEdit && remoteVisible" class="edit-section">
            <div class="edit-sec-title">
              远端信息（Civitai）
              <button
                type="button"
                class="btn-tonal sm"
                :disabled="metaBusy"
                @click="refreshEditLora"
              >
                <span class="mdi" :class="editLora && refreshingIds.has(editLora.id) ? 'mdi-loading mdi-spin' : 'mdi-refresh'" />刷新联网信息
              </button>
            </div>
            <div class="remote-grid">
              <div class="rg-item"><span class="rg-label">Civitai Model</span><span>{{ form.remote_model_name || '—' }}</span></div>
              <div class="rg-item"><span class="rg-label">Version</span><span>{{ form.remote_version_name || '—' }}</span></div>
              <div class="rg-item"><span class="rg-label">Creator</span><span>{{ form.remote_creator || '—' }}</span></div>
              <div class="rg-item"><span class="rg-label">Base Model</span><span>{{ form.remote_base_model || '—' }}</span></div>
              <div class="rg-item"><span class="rg-label">Metadata Host</span><span class="mono">{{ form.metadata_host || '—' }}</span></div>
              <div class="rg-item"><span class="rg-label">最近获取</span><span>{{ form.metadata_fetched_at ? formatTime(form.metadata_fetched_at) : '—' }}</span></div>
            </div>

            <!-- Usage Tips（Civitai version settings；全部无值时整块隐藏） -->
            <div v-if="usageTipsVisible" class="remote-block">
              <div class="rg-label">Usage Tips（Civitai 推荐，不会自动覆盖本地）</div>
              <div class="usage-grid">
                <div v-if="form.remote_recommended_strength != null" class="rg-item">
                  <span class="rg-label">Strength</span>
                  <span class="mono">{{ form.remote_recommended_strength.toFixed(2) }}</span>
                </div>
                <div v-if="form.remote_clip_skip != null" class="rg-item">
                  <span class="rg-label">Clip Skip</span>
                  <span class="mono">{{ form.remote_clip_skip }}</span>
                </div>
                <div v-if="form.remote_steps != null" class="rg-item">
                  <span class="rg-label">Steps</span>
                  <span class="mono">{{ form.remote_steps }}</span>
                </div>
                <div v-if="form.remote_epochs != null" class="rg-item">
                  <span class="rg-label">Epochs</span>
                  <span class="mono">{{ form.remote_epochs }}</span>
                </div>
              </div>
              <button
                v-if="form.remote_recommended_strength != null"
                type="button"
                class="btn-tonal sm mt-2"
                @click="adoptStrength"
              >
                <span class="mdi mdi-tune-vertical" />采用推荐权重（{{ form.remote_recommended_strength.toFixed(2) }}）
              </button>
            </div>

            <!-- Civitai Trigger Words（远端完整展示；采用需手动点击） -->
            <div v-if="remoteTrainedWordsList.length" class="remote-block">
              <div class="rg-label">Civitai Trigger Words（不会自动覆盖本地）</div>
              <div class="tw-chips">
                <span v-for="tw in remoteTrainedWordsList" :key="tw" class="tw-chip mono">{{ tw }}</span>
              </div>
              <button type="button" class="btn-primary sm mt-2" @click="adoptTrainedWords">
                <span class="mdi mdi-content-copy" />采用全部为本地 Trigger
              </button>
            </div>

            <!-- 模型简介（Civitai 模型主页面，read-only 纯文本） -->
            <div v-if="form.remote_model_description" class="remote-desc">
              <div class="rg-label">模型简介（纯文本展示，不执行 HTML）</div>
              <p class="remote-desc-text">{{ form.remote_model_description }}</p>
            </div>

            <!-- 版本说明（read-only 纯文本） -->
            <div v-if="form.remote_version_description" class="remote-desc">
              <div class="rg-label">版本说明</div>
              <p class="remote-desc-text">{{ form.remote_version_description }}</p>
            </div>

            <div v-if="remoteTagsList.length" class="remote-block">
              <div class="rg-label">Tags</div>
              <div class="tw-chips">
                <span v-for="t in remoteTagsList" :key="t" class="tw-chip">{{ t }}</span>
              </div>
            </div>
          </div>

          <!-- 技术信息（默认折叠，无绝对路径） -->
          <div v-if="isEdit" class="edit-section">
            <div class="edit-sec-title tech-toggle" @click="techOpen = !techOpen">
              <span class="mdi" :class="techOpen ? 'mdi-chevron-down' : 'mdi-chevron-right'" />
              技术信息
            </div>
            <div v-if="techOpen" class="tech-grid">
              <div class="rg-item"><span class="rg-label">SHA256</span><span class="mono ellipsis" :title="form.sha256 || ''">{{ form.sha256 || '—' }}</span></div>
              <div class="rg-item"><span class="rg-label">ComfyUI filename</span><span class="mono ellipsis" :title="form.filename">{{ form.filename }}</span></div>
              <div class="rg-item"><span class="rg-label">Civitai Model ID</span><span class="mono">{{ form.remote_model_id ?? '—' }}</span></div>
              <div class="rg-item"><span class="rg-label">Civitai Version ID</span><span class="mono">{{ form.remote_version_id ?? '—' }}</span></div>
              <div class="rg-item"><span class="rg-label">Civitai File ID</span><span class="mono">{{ form.remote_file_id ?? '—' }}</span></div>
            </div>
          </div>
        </div>

        <div class="dialog-foot">
          <button type="button" class="btn-tonal" @click="loraDialog = false">取消</button>
          <button type="button" class="btn-primary" :disabled="!form.name || !form.filename" @click="saveLora()">
            保存
          </button>
        </div>
      </div>
    </v-dialog>

    <!-- ══════════ Metadata 批量进度/汇总 Dialog ══════════ -->
    <v-dialog v-model="metaDialog" max-width="520px">
      <div class="m3-dialog">
        <div class="dialog-head">
          <span class="dialog-title">{{ metaBusy ? '正在补全 Metadata…' : 'Metadata 汇总' }}</span>
          <button type="button" class="dialog-close" @click="metaDialog = false">
            <span class="mdi mdi-close" />
          </button>
        </div>
        <div v-if="metaBusy" class="meta-progress-body">
          <div class="meta-progress-track">
            <div class="meta-progress-fill" :style="{ width: metaPct + '%' }" />
          </div>
          <p class="text-caption">正在处理 {{ metaDone }} / {{ metaTotal }}</p>
        </div>
        <div v-else class="meta-progress-body">
          <div v-if="metaResult" class="meta-summary">
            <div class="ms-item ok"><b>{{ metaResult.matched.length }}</b> 已匹配</div>
            <div class="ms-item warn"><b>{{ metaResult.not_found.length }}</b> 未找到</div>
            <div class="ms-item warn"><b>{{ metaResult.local_file_missing.length }}</b> 本地文件不存在</div>
            <div class="ms-item warn"><b>{{ metaResult.local_file_ambiguous.length }}</b> 本地文件歧义</div>
            <div class="ms-item err"><b>{{ metaResult.errors.length }}</b> 失败</div>
          </div>
          <p v-if="metaResult && metaResult.auth_warning" class="auth-warn">
            Civitai Token 无效，已使用公开访问。
          </p>
          <details v-if="metaResult && metaResult.errors.length" class="meta-errors">
            <summary>展开失败详情</summary>
            <p v-for="(e, i) in metaResult.errors.slice(0, 20)" :key="i" class="mono meta-err-line">{{ e.name || ('#' + e.id) }}：{{ e.detail }}</p>
          </details>
        </div>
        <div class="dialog-foot">
          <button type="button" class="btn-tonal" @click="metaDialog = false">关闭</button>
        </div>
      </div>
    </v-dialog>

    <!-- ══════════ 删除确认 Dialog ══════════ -->
    <v-dialog v-model="confirmDialog" max-width="420px">
      <div class="m3-dialog">
        <div class="dialog-head">
          <span class="dialog-title">{{ confirmTitle }}</span>
        </div>
        <p class="confirm-text">{{ confirmText }}</p>
        <div class="dialog-foot">
          <button type="button" class="btn-tonal" @click="confirmDialog = false">取消</button>
          <button type="button" class="btn-danger" @click="confirmAction">删除</button>
        </div>
      </div>
    </v-dialog>

    <v-snackbar v-model="snackbar" :timeout="2600" :color="snackbarColor">
      {{ snackbarText }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useLoraStore } from '../stores/lora'
import { useStudioStore } from '../stores/studio'
import { useBulkSelection } from '../composables/useBulkSelection'
import BulkSelectionBar from '../components/BulkSelectionBar.vue'
import type { Lora, LoraSource, ScanCandidate, MetadataStatus } from '../types'

const loraStore = useLoraStore()
const studioStore = useStudioStore()

const searchQuery = ref('')
const onlyFavorites = ref(false)

const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

/* ── 视图模式（卡片/列表，localStorage 记忆，spec §38） ── */
const VIEW_KEY = 'imageforge_lora_view'
const viewMode = ref<'card' | 'list'>('card')
function setViewMode(mode: 'card' | 'list') {
  viewMode.value = mode
  try { localStorage.setItem(VIEW_KEY, mode) } catch { /* ignore */ }
}

/* ── 来源管理 ── */
const sourceDialog = ref(false)
const newSourcePath = ref('')
const newSourceRecursive = ref(true)
const addingSource = ref(false)
const sourceError = ref('')
const newSourceResolved = ref('')
const resolveStatus = ref<{ ok: boolean; error?: string; count?: number } | null>(null)
let resolveTimer: ReturnType<typeof setTimeout> | null = null

/* ── 扫描预览 ── */
const scanDialog = ref(false)
const scanResult = ref<null | { source: LoraSource; candidates: ScanCandidate[]; summary: any }>(null)
const selectedPaths = ref<Set<string>>(new Set())
const importing = ref(false)

/* ── LoRA 编辑 ── */
const loraDialog = ref(false)
const isEdit = ref(false)
const techOpen = ref(false)
const editLora = ref<Lora | null>(null)
const form = ref<any>({
  id: undefined, name: '', filename: '', trigger_words: '', description: '',
  default_strength: 0.8, is_favorite: false, cover_hidden: false, category: '通用',
  is_custom: true, is_valid_file: true,
})

/* ── Metadata 批量刷新 ── */
const metaBusy = ref(false)
const metaDialog = ref(false)
const metaDone = ref(0)
const metaTotal = ref(0)
const metaResult = ref<any>(null)
const refreshingIds = ref<Set<number>>(new Set())
const coverErrored = ref<Set<number>>(new Set())

/* ── 删除确认 ── */
const confirmDialog = ref(false)
const confirmTitle = ref('')
const confirmText = ref('')
let confirmAction: () => void = () => {}

const filteredLoras = computed(() => {
  return loraStore.loras.filter(l => {
    const matchFav = !onlyFavorites.value || l.is_favorite
    const q = searchQuery.value.toLowerCase()
    const matchQuery = !q ||
      l.name.toLowerCase().includes(q) ||
      (l.trigger_words && l.trigger_words.toLowerCase().includes(q))
    return matchFav && matchQuery
  })
})

const bulkSel = useBulkSelection(() => filteredLoras.value)

const strengthPct = computed(() => ((form.value.default_strength - 0.1) / 1.4) * 100)
const metaPct = computed(() => (metaTotal.value ? Math.round((metaDone.value / metaTotal.value) * 100) : 0))

const remoteTrainedWordsList = computed(() => {
  try {
    const v = form.value.remote_trained_words
    return v ? JSON.parse(v) : []
  } catch { return [] }
})
const remoteTagsList = computed(() => {
  try {
    const v = form.value.remote_tags
    return v ? JSON.parse(v) : []
  } catch { return [] }
})
const remoteVisible = computed(() => !!editLora.value)
const usageTipsVisible = computed(() =>
  form.value.remote_recommended_strength != null ||
  form.value.remote_clip_skip != null ||
  form.value.remote_steps != null ||
  form.value.remote_epochs != null,
)

/* ── Card/List 触发词展示：local 优先，Civitai trainedWords fallback（§9/§10） ── */
function remoteTriggerWords(lora: Lora): string[] {
  try {
    const arr = lora.remote_trained_words ? JSON.parse(lora.remote_trained_words) : []
    return Array.isArray(arr) ? arr.filter(w => typeof w === 'string' && w.trim()) : []
  } catch { return [] }
}
function remoteTriggerText(lora: Lora): string {
  return remoteTriggerWords(lora).join(', ')
}

const selectedCandidates = computed(() =>
  scanResult.value ? scanResult.value.candidates.filter(c => selectedPaths.value.has(c.full_path)) : [],
)

onMounted(() => {
  loraStore.fetchLoras()
  loraStore.fetchSources()
  try {
    const saved = localStorage.getItem(VIEW_KEY)
    if (saved === 'card' || saved === 'list') viewMode.value = saved
  } catch { /* ignore */ }
})

function notify(text: string, color = 'success') {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

/* ── 封面（只走本地 backend /api/loras/{id}/cover，spec §66） ── */
function coverSrc(lora: Lora): string {
  if (!lora.id || coverErrored.value.has(lora.id)) return ''
  return `/api/loras/${lora.id}/cover`
}
function onCoverError(lora: Lora) {
  coverErrored.value.add(lora.id)
}

/* ── Metadata 状态（spec §53/§63） ── */
function metaStatusText(lora: Lora): string {
  const s: MetadataStatus = lora.metadata_status ?? null
  if (s === 'matched') return '已匹配'
  if (s === 'not_found') return '未找到'
  if (s === 'remote_error') return '失败'
  if (s === 'rate_limited') return '限流'
  if (s === 'local_file_not_found') return '本地文件缺失'
  if (s === 'local_file_ambiguous') return '本地文件歧义'
  if (s === 'hash_file_mismatch') return '哈希不符'
  return '未获取'
}
function metaStatusClass(lora: Lora): string {
  const s: MetadataStatus = lora.metadata_status ?? null
  if (s === 'matched') return 'ok'
  if (s === 'not_found' || s === 'hash_file_mismatch') return 'warn'
  if (s === 'remote_error' || s === 'rate_limited') return 'err'
  if (s === 'local_file_not_found' || s === 'local_file_ambiguous') return 'err'
  return 'idle'
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false })
  } catch { return iso }
}

function openCivitai(lora: Lora) {
  if (!lora.remote_model_id || !lora.metadata_host) return
  window.open(`https://${lora.metadata_host}/models/${lora.remote_model_id}`, '_blank', 'noopener')
}

/* ── 单条刷新 ── */
async function refreshEditLora() {
  if (editLora.value) await refreshOne(editLora.value)
}
async function refreshOne(lora: Lora) {
  if (!lora.id || metaBusy.value) return
  refreshingIds.value.add(lora.id)
  try {
    const res = await loraStore.refreshMetadata(lora.id)
    coverErrored.value.delete(lora.id)
    // 若编辑对话框正打开这条 LoRA，同步远端区
    if (editLora.value?.id === lora.id) {
      const fresh = loraStore.loras.find(x => x.id === lora.id)
      if (fresh) form.value = { is_custom: true, ...fresh }
    }
    if (res.status === 'matched') notify(`已匹配：${res.remote_model_name || lora.name}`)
    else if (res.status === 'not_found') notify('两个官方 host 均未找到', 'warning')
    else if (res.status === 'hash_file_mismatch') notify('远端 files 无匹配 SHA256', 'error')
    else if (res.status === 'local_file_not_found') notify('本地文件不存在或已移动', 'error')
    else if (res.status === 'local_file_ambiguous') notify('多个同名文件，无法确定目标', 'error')
    else notify(`刷新失败：${res.detail || res.status}`, 'error')
  } catch (err: any) {
    notify(err.response?.data?.detail?.summary || err.message || '刷新失败', 'error')
  } finally {
    refreshingIds.value.delete(lora.id)
  }
}

/* ── 批量补全（选中 或 当前过滤结果，spec §58） ── */
async function openBulkMetadata() {
  if (bulkSel.selected.length === 0) return
  await runBatch([...bulkSel.selected])
}
async function refreshCurrentFilter() {
  if (filteredLoras.value.length === 0) return
  await runBatch(filteredLoras.value.map(l => l.id))
}
async function runBatch(ids: Array<number | string>) {
  metaBusy.value = true
  metaDialog.value = true
  metaResult.value = null
  metaDone.value = 0
  metaTotal.value = ids.length
  try {
    // 后端批量接口一次性返回；前端用进度模拟展示（spec §59 只出一个汇总 UI）
    const step = Math.max(1, Math.floor(ids.length / 8))
    const tick = setInterval(() => {
      metaDone.value = Math.min(metaTotal.value, metaDone.value + step)
      if (metaDone.value >= metaTotal.value) clearInterval(tick)
    }, 180)
    const res = await loraStore.refreshMetadataBatch(ids)
    clearInterval(tick)
    metaDone.value = metaTotal.value
    metaResult.value = res
    bulkSel.clear()
  } catch (err: any) {
    notify(err.response?.data?.detail || err.message || '批量补全失败', 'error')
    metaDialog.value = false
  } finally {
    metaBusy.value = false
  }
}

/* ── 采用 Civitai Trigger（走现有 PUT /api/loras/{id}，spec §28/§34） ── */
async function adoptTrainedWords() {
  if (!editLora.value || !remoteTrainedWordsList.value.length) return
  const joined = remoteTrainedWordsList.value.join(', ')
  form.value.trigger_words = joined
  await saveLora(false)
  notify('已采用 Civitai 推荐 Trigger 为本地 Trigger')
}

/* ── 采用 Civitai 推荐权重（本地 default_strength 权威，手动采用才变化，§14/§33） ── */
async function adoptStrength() {
  if (!editLora.value || form.value.remote_recommended_strength == null) return
  form.value.default_strength = form.value.remote_recommended_strength
  await saveLora(false)
  notify(`已采用 Civitai 推荐权重 ${form.value.remote_recommended_strength.toFixed(2)}`)
}

/* ── 来源管理 ── */
async function openSourceDialog() {
  sourceError.value = ''
  await loraStore.fetchSources()
  sourceDialog.value = true
}

function resolvePreview() {
  const p = newSourcePath.value.trim()
  if (!p) {
    newSourceResolved.value = ''
    resolveStatus.value = null
    sourceError.value = ''
    return
  }
  if (resolveTimer) clearTimeout(resolveTimer)
  resolveTimer = setTimeout(async () => {
    try {
      const r = await loraStore.resolvePath(p)
      newSourceResolved.value = r.resolved_path
      if (r.exists && r.is_dir && r.readable) {
        resolveStatus.value = { ok: true, count: r.lora_file_count }
        sourceError.value = ''
      } else {
        resolveStatus.value = { ok: false, error: r.error || '路径不可访问' }
      }
    } catch {
      resolveStatus.value = { ok: false, error: '路径解析失败' }
    }
  }, 200)
}

async function addSource() {
  sourceError.value = ''
  const p = newSourcePath.value.trim()
  if (!p) return
  addingSource.value = true
  try {
    await loraStore.addSource(p, newSourceRecursive.value)
    newSourcePath.value = ''
    newSourceResolved.value = ''
    notify('来源已添加')
  } catch (err: any) {
    sourceError.value = err.response?.data?.detail || err.message || '添加来源失败'
  } finally {
    addingSource.value = false
  }
}

async function runScan(s: LoraSource) {
  try {
    const result = await loraStore.scanSource(s.id)
    if (result) {
      scanResult.value = result
      selectedPaths.value = new Set()
      scanDialog.value = true
    }
  } catch (err: any) {
    notify(err.response?.data?.detail || err.message || '扫描失败', 'error')
  }
}

function askDeleteSource(s: LoraSource) {
  confirmTitle.value = '删除来源'
  confirmText.value = `删除来源「${s.display_path}」不会删除已导入的 LoRA 库记录。确定删除该来源吗？`
  confirmAction = async () => {
    await loraStore.deleteSource(s.id)
    notify('来源已删除，LoRA 库记录保留')
    confirmDialog.value = false
  }
  confirmDialog.value = true
}

/* ── 扫描预览选择 ── */
function isSelected(c: ScanCandidate) {
  return selectedPaths.value.has(c.full_path)
}
function toggleCandidate(c: ScanCandidate) {
  if (c.exists_in_db) return
  const s = new Set(selectedPaths.value)
  if (s.has(c.full_path)) s.delete(c.full_path)
  else s.add(c.full_path)
  selectedPaths.value = s
}
function selectAllNew() {
  if (!scanResult.value) return
  selectedPaths.value = new Set(
    scanResult.value.candidates.filter(c => !c.exists_in_db).map(c => c.full_path),
  )
}
function clearSelection() {
  selectedPaths.value = new Set()
}
async function doImport() {
  if (selectedCandidates.value.length === 0 || !scanResult.value) return
  importing.value = true
  try {
    const res = await loraStore.importCandidates(
      scanResult.value.source.id,
      selectedCandidates.value.map(c => c.relative_path),
    )
    studioStore.syncLorasFromLibrary(loraStore.loras)
    const skippedN = (res.skipped || []).length
    const errN = (res.errors || []).length
    const importedN = (res.imported || []).length
    notify(`已导入 ${importedN} 项${skippedN ? `，跳过 ${skippedN}` : ''}${errN ? `，${errN} 项失败` : ''}`)
    scanDialog.value = false
    // 可选小改动（spec §37）：导入后可一键补全 Metadata
    if (importedN > 0) {
      snackbarText.value = `已导入 ${importedN} 项 LoRA —— 可用「补全当前结果」获取 Civitai 元数据`
      snackbar.value = true
    }
  } catch (err: any) {
    notify(err.response?.data?.detail || err.message || '导入失败', 'error')
  } finally {
    importing.value = false
  }
}

/* ── LoRA 编辑 ── */
function openCreateDialog() {
  isEdit.value = false
  editLora.value = null
  techOpen.value = false
  form.value = {
    id: undefined, name: '', filename: '', trigger_words: '', description: '',
    default_strength: 0.8, is_favorite: false, cover_hidden: false, category: '通用',
    is_custom: true, is_valid_file: true,
  }
  loraDialog.value = true
}
function openEditDialog(lora: Lora) {
  isEdit.value = true
  editLora.value = lora
  techOpen.value = false
  form.value = { is_custom: true, ...lora }
  loraDialog.value = true
}
async function saveLora(showMsg = true) {
  await loraStore.saveLora(form.value)
  studioStore.syncLorasFromLibrary(loraStore.loras)
  await studioStore.buildPrompt()
  loraDialog.value = false
  if (showMsg) notify('LoRA 配置已保存并同步至创作台')
}
function askDeleteLora(lora: Lora) {
  confirmTitle.value = '删除 LoRA 记录'
  confirmText.value = `确定删除「${lora.name}」吗？该操作只删除库记录，不影响磁盘文件。`
  confirmAction = async () => {
    await loraStore.deleteLora(lora.id)
    studioStore.syncLorasFromLibrary(loraStore.loras)
    confirmDialog.value = false
    notify('已删除')
  }
  confirmDialog.value = true
}

/* ── 批量删除 ── */
function openBulkDelete() {
  if (bulkSel.selected.length === 0) return
  confirmTitle.value = `删除所选 ${bulkSel.selected.length} 项 LoRA 记录`
  confirmText.value = '确定删除所选 LoRA 库记录吗？该操作只删除库记录，不影响磁盘文件。'
  confirmAction = async () => {
    try {
      const failed: Array<number | string> = []
      for (const id of bulkSel.selected) {
        try { await loraStore.deleteLora(Number(id)) } catch { failed.push(id) }
      }
      studioStore.syncLorasFromLibrary(loraStore.loras)
      bulkSel.clear()
      if (failed.length) notify(`删除失败 ${failed.length} 项`, 'error')
      else notify('已删除所选 LoRA 记录')
    } finally {
      confirmDialog.value = false
    }
  }
  confirmDialog.value = true
}

/* ── 默认权重 slider ── */
function onStrengthDown(e: PointerEvent) {
  if (e.button !== 0) return
  const track = e.currentTarget as HTMLElement
  const apply = (clientX: number) => {
    const rect = track.getBoundingClientRect()
    const p = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width))
    form.value.default_strength = Math.round((0.1 + p * 1.4) / 0.05) * 0.05
  }
  apply(e.clientX)
  const move = (ev: PointerEvent) => apply(ev.clientX)
  const up = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
}
</script>

<style scoped>
.lib-root {
  padding: 24px 28px 40px;
  color: rgb(var(--v-theme-on-surface));
}
.lib-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.lib-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.lib-sub {
  margin: 6px 0 0;
  font-size: 13.5px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.lib-actions {
  display: flex;
  gap: 10px;
}

/* ── 按钮 ── */
.btn-primary, .btn-tonal, .btn-ghost, .btn-danger {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 0;
  border-radius: 999px;
  padding: 11px 20px;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--motion-emphasized),
    opacity var(--motion-fast) var(--motion-emphasized);
}
.btn-primary {
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
}
.btn-primary:hover { background: rgb(var(--v-theme-primary-darken-1)); }
.btn-primary:disabled { opacity: 0.45; cursor: default; }
.btn-tonal {
  background: rgb(var(--v-theme-primary-container));
  color: rgb(var(--v-theme-on-primary-container));
}
.btn-tonal:hover { background: rgb(var(--v-theme-secondary-container)); }
.btn-ghost {
  background: transparent;
  color: rgb(var(--v-theme-primary));
}
.btn-danger {
  background: rgb(var(--v-theme-error-container));
  color: rgb(var(--v-theme-error));
}
.btn-primary.sm, .btn-tonal.sm, .btn-ghost.sm {
  padding: 8px 14px;
  font-size: 13px;
}

/* ── Filter Bar ── */
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px;
  border-radius: 24px;
  background: rgb(var(--v-theme-surface-container));
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.search-field {
  position: relative;
  flex: 1;
  min-width: 220px;
  display: flex;
  align-items: center;
  border-radius: 16px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgb(var(--v-theme-outline-variant));
  transition: border-color var(--motion-fast) var(--motion-emphasized),
    box-shadow var(--motion-fast) var(--motion-emphasized);
}
.search-field:focus-within {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 0 0 3px rgba(var(--v-theme-primary), 0.12);
}
.search-icon {
  position: absolute;
  left: 14px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 18px;
  pointer-events: none;
}
.search-input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  padding: 12px 38px 12px 42px;
  font-family: var(--font-sans);
  font-size: 14.5px;
  color: rgb(var(--v-theme-on-surface));
}
.search-clear {
  position: absolute;
  right: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
}
.filter-side {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.view-toggle {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface));
}
.vt-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 28px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 15px;
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--motion-emphasized),
    color var(--motion-fast) var(--motion-emphasized);
}
.vt-btn.on {
  background: rgb(var(--v-theme-secondary-container));
  color: rgb(var(--v-theme-on-secondary-container));
}
.fav-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  border: 0;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface-variant));
  font-family: var(--font-sans);
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
}
.fav-btn.on {
  background: rgb(var(--v-theme-secondary-container));
  color: rgb(var(--v-theme-on-secondary-container));
}
.count-mono {
  font-size: 12.5px;
  color: rgb(var(--v-theme-on-surface-variant));
  white-space: nowrap;
}

/* ── Empty ── */
.lib-empty {
  text-align: center;
  padding: 70px 0;
  color: rgb(var(--v-theme-on-surface-variant));
}
.lib-empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  margin: 0 auto 14px;
  border-radius: 20px;
  background: rgb(var(--v-theme-surface-container));
  font-size: 30px;
}
.lib-empty p { margin: 0 0 4px; font-size: 14.5px; font-weight: 600; }
.lib-empty-hint { font-weight: 400 !important; font-size: 13px !important; }

/* ── CARD VIEW ── */
.lora-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(272px, 1fr));
  gap: 18px;
}
.lora-card {
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 20px;
  background: rgb(var(--v-theme-surface));
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: border-color var(--motion-fast) var(--motion-emphasized),
    box-shadow var(--motion-fast) var(--motion-emphasized);
}
.lora-card:hover {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08);
}
.lora-card.selected {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 0 0 2px rgba(var(--v-theme-primary), 0.35);
}
.card-cover {
  position: relative;
  aspect-ratio: 4 / 3;
  background: rgb(var(--v-theme-surface-container-low));
  overflow: hidden;
}
.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.cover-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 6px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 13px;
}
.cover-empty .mdi { font-size: 28px; opacity: 0.55; }
.card-check {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 5;
  padding: 4px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.78);
}
.card-cover .fav-star {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 5;
  background: rgba(0, 0, 0, 0.45) !important;
  color: #fff;
}
.card-body {
  padding: 14px 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-grow: 1;
}
.card-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.card-name {
  font-size: 15px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-fav-mini { color: rgb(var(--v-theme-warning)); font-size: 13px; flex-shrink: 0; }
.card-remote-name {
  font-size: 12.5px;
  color: rgb(var(--v-theme-primary));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-version {
  font-size: 12px;
  color: rgb(var(--v-theme-on-surface-variant));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-trigger {
  margin-top: 6px;
  font-size: 12.5px;
  color: rgb(var(--v-theme-on-surface));
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 34px;
}
.card-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
  padding-top: 10px;
}
.weight { font-size: 13px; font-weight: 700; }
.card-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  border-top: 1px solid rgb(var(--v-theme-outline-variant));
  margin-top: 10px;
  padding-top: 8px;
}
.op-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 9px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 12.5px;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--motion-emphasized);
}
.op-btn:hover { background: rgb(var(--v-theme-surface-container)); }
.op-btn.danger:hover { background: rgb(var(--v-theme-error-container)); color: rgb(var(--v-theme-error)); }
.op-btn.external:hover { background: rgb(var(--v-theme-secondary-container)); }
.op-btn:disabled { opacity: 0.4; cursor: default; }

/* ── LIST VIEW（无封面） ── */
.lora-list {
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 20px;
  background: rgb(var(--v-theme-surface));
  overflow: hidden;
}
.lora-head, .lora-row {
  display: grid;
  grid-template-columns: 44px 44px minmax(0, 1.5fr) minmax(0, 1.4fr) 72px 120px 110px 96px 120px;
  align-items: center;
  min-width: 0;
}
.lora-head {
  padding: 12px 16px;
  background: rgb(var(--v-theme-surface-container));
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: rgb(var(--v-theme-on-surface-variant));
}
.lora-row {
  padding: 12px 16px;
  border-top: 1px solid rgb(var(--v-theme-outline-variant));
  min-width: 0;
  transition: background-color var(--motion-fast) var(--motion-emphasized);
}
.lora-row:hover { background: rgb(var(--v-theme-surface-container-low)); }
.cell { min-width: 0; }
.col-fav { text-align: center; }
.col-check { display: flex; align-items: center; justify-content: center; }
.col-ops { display: flex; justify-content: flex-end; gap: 2px; }
.head-check {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}
.head-check input[type="checkbox"] {
  width: 17px;
  height: 17px;
  accent-color: rgb(var(--v-theme-primary));
  cursor: pointer;
}
.fav-star {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: rgb(var(--v-theme-outline));
  cursor: pointer;
  font-size: 16px;
}
.fav-star.on { color: rgb(var(--v-theme-warning)); }
.name-line { display: flex; align-items: center; gap: 8px; min-width: 0; }
.lora-name {
  font-size: 14px;
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cat-pill {
  flex-shrink: 0;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container));
  font-size: 11.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
}
.trigger { font-size: 12.5px; color: rgb(var(--v-theme-primary)); }
.col-trigger .ellipsis { display: block; max-width: 100%; }
.none-hint { font-size: 12.5px; color: rgb(var(--v-theme-text-muted)); font-style: italic; }
.ellipsis { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mono { font-family: var(--font-mono); }

/* ── Status / Meta badges ── */
.status-badge, .meta-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}
.status-badge.ok { background: rgb(var(--v-theme-surface-container)); color: rgb(var(--v-theme-success)); }
.status-badge.bad { background: rgb(var(--v-theme-error-container)); color: rgb(var(--v-theme-error)); }
.status-badge .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.meta-badge.ok { background: rgb(var(--v-theme-primary-container)); color: rgb(var(--v-theme-on-primary-container)); }
.meta-badge.idle { background: rgb(var(--v-theme-surface-container)); color: rgb(var(--v-theme-on-surface-variant)); }
.meta-badge.warn { background: rgb(var(--v-theme-warning)); color: #fff; }
.meta-badge.err { background: rgb(var(--v-theme-error-container)); color: rgb(var(--v-theme-error)); }

/* ── Dialog 公共 ── */
.m3-dialog {
  background: rgb(var(--v-theme-surface));
  border-radius: 24px;
  overflow: hidden;
}
.dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 10px;
}
.dialog-title { font-size: 18px; font-weight: 700; letter-spacing: -0.01em; }
.dialog-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 18px;
  cursor: pointer;
}
.dialog-close:hover { background: rgb(var(--v-theme-surface-container)); }
.dialog-hint {
  margin: 0;
  padding: 0 24px 12px;
  font-size: 13px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.dialog-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 24px 20px;
}
.foot-hint { margin-right: auto; font-size: 13px; color: rgb(var(--v-theme-on-surface-variant)); }
.confirm-text {
  margin: 0;
  padding: 0 24px;
  font-size: 14px;
  line-height: 1.6;
  color: rgb(var(--v-theme-on-surface-variant));
}

/* ── Edit Dialog：三区 ── */
.edit-sections {
  padding: 4px 24px 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 62vh;
  overflow-y: auto;
}
.edit-section {
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 16px;
  padding: 14px;
  background: rgb(var(--v-theme-surface-container-low));
}
.edit-sec-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: rgb(var(--v-theme-primary));
  margin-bottom: 10px;
}
.tech-toggle { cursor: pointer; margin-bottom: 0; }
.form-body { display: flex; flex-direction: column; gap: 12px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field-label { font-size: 12.5px; font-weight: 600; color: rgb(var(--v-theme-on-surface-variant)); }
.field-input {
  width: 100%;
  box-sizing: border-box;
  padding: 11px 13px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 12px;
  background: rgb(var(--v-theme-surface));
  font-family: var(--font-sans);
  font-size: 14px;
  color: rgb(var(--v-theme-on-surface));
}
.field-input:focus { outline: none; border-color: rgb(var(--v-theme-primary)); box-shadow: 0 0 0 3px rgba(var(--v-theme-primary), 0.12); }
.edit-check {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
  font-size: 13px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.edit-check input[type="checkbox"] { width: 16px; height: 16px; accent-color: rgb(var(--v-theme-primary)); cursor: pointer; }
.check-label { font-size: 13px; }
.strength-field { padding-top: 4px; }
.mini-slider { margin-top: 10px; height: 20px; display: flex; align-items: center; cursor: pointer; }
.ms-track { position: relative; width: 100%; height: 5px; border-radius: 999px; background: rgb(var(--v-theme-surface-container-highest)); }
.ms-fill { position: absolute; left: 0; top: 0; height: 100%; border-radius: 999px; background: rgb(var(--v-theme-primary)); }
.ms-thumb { position: absolute; top: 50%; width: 18px; height: 18px; border-radius: 50%; transform: translate(-50%, -50%); background: rgb(var(--v-theme-surface)); border: 2.5px solid rgb(var(--v-theme-primary)); pointer-events: none; }

.remote-grid, .tech-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 16px;
}
.rg-item { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.rg-label { font-size: 11.5px; font-weight: 600; color: rgb(var(--v-theme-on-surface-variant)); }
.rg-item > span:last-child { font-size: 13px; color: rgb(var(--v-theme-on-surface)); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.remote-tw { margin-top: 10px; }
.remote-block { margin-top: 12px; }
.usage-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
  gap: 8px 16px;
  margin-top: 6px;
}
.tw-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.tw-chip { padding: 4px 10px; border-radius: 999px; background: rgb(var(--v-theme-surface-container)); font-size: 12px; color: rgb(var(--v-theme-on-surface)); }
.remote-desc { margin-top: 12px; }
.remote-desc-text {
  margin: 6px 0 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: rgb(var(--v-theme-on-surface-variant));
  max-height: 140px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ── Civitai 远端 fallback 展示（Card/List） ── */
.tw-src {
  display: inline-block;
  margin-right: 6px;
  padding: 1px 7px;
  border-radius: 999px;
  background: rgb(var(--v-theme-secondary-container));
  color: rgb(var(--v-theme-on-secondary-container));
  font-size: 10.5px;
  font-weight: 700;
  vertical-align: 1px;
}
.rec-weight {
  font-size: 11.5px;
  font-weight: 650;
  color: rgb(var(--v-theme-on-surface-variant));
  white-space: nowrap;
}
.weight-cell { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.rec-mini { font-size: 11px; color: rgb(var(--v-theme-on-surface-variant)); white-space: nowrap; }
.trigger.remote { color: rgb(var(--v-theme-on-surface-variant)); }

/* ── Metadata 批量进度/汇总 ── */
.meta-progress-body { padding: 8px 24px 4px; }
.meta-progress-track { height: 6px; border-radius: 999px; background: rgb(var(--v-theme-surface-container-highest)); overflow: hidden; }
.meta-progress-fill { height: 100%; border-radius: 999px; background: rgb(var(--v-theme-primary)); transition: width 160ms var(--motion-emphasized); }
.meta-summary { display: flex; flex-wrap: wrap; gap: 8px; }
.ms-item { padding: 8px 14px; border-radius: 999px; background: rgb(var(--v-theme-surface-container)); font-size: 12.5px; color: rgb(var(--v-theme-on-surface-variant)); }
.ms-item b { margin-right: 6px; font-size: 14px; }
.ms-item.ok { background: rgb(var(--v-theme-primary-container)); color: rgb(var(--v-theme-on-primary-container)); }
.ms-item.warn { background: rgb(var(--v-theme-warning)); color: #fff; }
.ms-item.err { background: rgb(var(--v-theme-error-container)); color: rgb(var(--v-theme-error)); }
.auth-warn { margin: 10px 0 0; font-size: 12.5px; color: rgb(var(--v-theme-warning)); }
.meta-errors { margin-top: 10px; font-size: 12.5px; }
.meta-errors summary { cursor: pointer; color: rgb(var(--v-theme-on-surface-variant)); }
.meta-err-line { font-size: 11.5px; color: rgb(var(--v-theme-error)); margin: 3px 0; }

/* ── 来源管理 ── */
.add-source { display: flex; align-items: center; gap: 10px; padding: 0 24px; }
.path-input {
  flex: 1;
  min-width: 0;
  padding: 12px 14px;
  border: 1px solid rgb(var(--v-theme-outline));
  border-radius: 14px;
  background: rgb(var(--v-theme-surface-container-low));
  font-size: 13.5px;
  color: rgb(var(--v-theme-on-surface));
}
.path-input:focus { outline: none; border-color: rgb(var(--v-theme-primary)); }
.rec-check {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  flex-shrink: 0;
}
.rec-check input { display: none; }
.rec-box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  border: 2px solid rgb(var(--v-theme-outline));
  color: #fff;
  font-size: 12px;
}
.rec-check input:checked + .rec-box { background: rgb(var(--v-theme-primary)); border-color: rgb(var(--v-theme-primary)); }
.form-error { margin: 8px 24px 0; font-size: 12.5px; color: rgb(var(--v-theme-error)); }
.path-preview { display: flex; align-items: center; gap: 10px; margin: 8px 24px 0; font-size: 12.5px; }
.pv-label { color: rgb(var(--v-theme-on-surface-variant)); flex-shrink: 0; }
.pv-path { color: rgb(var(--v-theme-primary)); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pv-dot { width: 8px; height: 8px; border-radius: 50%; background: rgb(var(--v-theme-success)); flex-shrink: 0; }
.pv-dot.bad { background: rgb(var(--v-theme-error)); }
.source-list { max-height: 44vh; overflow-y: auto; overflow-x: hidden; padding: 12px 16px; }
.source-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  margin-bottom: 8px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 14px;
  background: rgb(var(--v-theme-surface-container-low));
  min-width: 0;
}
.source-row .dot { flex-shrink: 0; width: 8px; height: 8px; border-radius: 50%; }
.dot.ok { background: rgb(var(--v-theme-success)); }
.dot.bad { background: rgb(var(--v-theme-error)); }
.source-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.src-display { font-size: 13px; color: rgb(var(--v-theme-on-surface)); }
.src-resolved { font-size: 12px; color: rgb(var(--v-theme-on-surface-variant)); }
.src-invalid { font-size: 12px; color: rgb(var(--v-theme-error)); }
.source-ops { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.mini-switch {
  position: relative;
  width: 36px;
  height: 22px;
  border: 0;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container-highest));
  cursor: pointer;
}
.mini-switch.on { background: rgb(var(--v-theme-primary)); }
.mini-switch .knob {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transition: transform var(--motion-fast) var(--motion-spring);
}
.mini-switch.on .knob { transform: translateX(14px); }
.mini-chip {
  padding: 5px 10px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 999px;
  background: transparent;
  font-size: 11.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
}
.mini-chip.on { background: rgb(var(--v-theme-secondary-container)); border-color: transparent; color: rgb(var(--v-theme-on-secondary-container)); }
.src-empty { padding: 26px 0; text-align: center; font-size: 13px; color: rgb(var(--v-theme-on-surface-variant)); }

/* ── 扫描预览 ── */
.scan-body { padding: 0 24px; }
.scan-summary { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.sum-item {
  padding: 7px 14px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container));
  font-size: 12.5px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.sum-item b { margin-right: 6px; font-size: 14px; }
.sum-item.primary { background: rgb(var(--v-theme-primary-container)); color: rgb(var(--v-theme-on-primary-container)); }
.sum-item.warn { background: rgb(var(--v-theme-warning)); color: #fff; }
.sum-item.err { background: rgb(var(--v-theme-error-container)); color: rgb(var(--v-theme-error)); }
.sum-item.muted { opacity: 0.75; }
.scan-toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.scan-path { flex: 1; min-width: 0; font-size: 12px; color: rgb(var(--v-theme-on-surface-variant)); text-align: right; }
.cand-list { border: 1px solid rgb(var(--v-theme-outline-variant)); border-radius: 16px; overflow: hidden; max-height: 46vh; overflow-y: auto; }
.cand-head, .cand-row { display: grid; grid-template-columns: 44px minmax(0, 1.4fr) minmax(0, 1fr); align-items: center; min-width: 0; }
.cand-head { padding: 10px 14px; background: rgb(var(--v-theme-surface-container)); font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: rgb(var(--v-theme-on-surface-variant)); }
.cand-row { padding: 10px 14px; border-top: 1px solid rgb(var(--v-theme-outline-variant)); min-width: 0; }
.cand-row.disabled { opacity: 0.55; }
.row-check {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 7px;
  border: 2px solid rgb(var(--v-theme-outline));
  background: transparent;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}
.row-check.on { background: rgb(var(--v-theme-primary)); border-color: rgb(var(--v-theme-primary)); }
.row-check:disabled { cursor: default; }
.c-name { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.cand-name { font-size: 13.5px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cand-path { font-size: 11.5px; color: rgb(var(--v-theme-on-surface-variant)); }
.c-flag { display: flex; flex-wrap: wrap; gap: 4px; }
.flag { padding: 3px 9px; border-radius: 999px; font-size: 11.5px; font-weight: 600; white-space: nowrap; }
.flag.ok { background: rgb(var(--v-theme-primary-container)); color: rgb(var(--v-theme-on-primary-container)); }
.flag.done { background: rgb(var(--v-theme-surface-container)); color: rgb(var(--v-theme-on-surface-variant)); }
.flag.warn { background: rgb(var(--v-theme-warning)); color: #fff; }
.flag.err { background: rgb(var(--v-theme-error-container)); color: rgb(var(--v-theme-error)); }

.mdi-spin { animation: mdi-spin 1s linear infinite; }
@keyframes mdi-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 16px; }
.pt-2 { padding-top: 8px; }
.mt-2 { margin-top: 8px; }
.text-caption { font-size: 12.5px; color: rgb(var(--v-theme-on-surface-variant)); }
.d-flex { display: flex; }
.align-center { align-items: center; }
</style>
