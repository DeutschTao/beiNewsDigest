/**
 * æ°é»æºç®¡çé¡µé»è¾ï¼v2 - æ°å¢ç±»åéæ©ï¼
 */
const newsService = require('../../services/news.js');

Page({
  data: {
    activeTab: 'preset',
    loading: true,
    adding: false,
    sourceType: 'rss',
    customName: '',
    customUrl: '',
    presetSources: [],
    customSources: [],
    allSources: [],
  },

  onLoad() {
    this.loadSources();
  },

  async loadSources() {
    this.setData({ loading: true });
    try {
      const res = await newsService.getSources();
      const data = res?.data || res;
      if (data) {
        const all = [
          ...(data.preset_sources || []).map(s => ({ ...s, _status: null, _checking: false })),
          ...(data.custom_sources || []).map(s => ({ ...s, _status: null, _checking: false })),
        ];
        this.setData({
          presetSources: data.preset_sources || [],
          customSources: data.custom_sources || [],
          allSources: all,
          loading: false,
        });
      } else {
        this.setData({ loading: false });
      }
    } catch (err) {
      console.error('loadSources failed:', err);
      this.setData({ loading: false });
    }
  },

  onTabChange(e) {
    const { tab } = e.currentTarget.dataset;
    this.setData({ activeTab: tab });
  },

  onSelectType(e) {
    const { type } = e.currentTarget.dataset;
    if (type !== this.data.sourceType) {
      this.setData({ sourceType: type, customUrl: '', customName: '' });
    }
  },

  onNameInput(e) {
    this.setData({ customName: e.detail.value });
  },

  onUrlInput(e) {
    this.setData({ customUrl: e.detail.value });
  },

  async onAddSource() {
    if (!this.data.customUrl || this.data.adding) return;
    this.setData({ adding: true });
    try {
      const res = await newsService.addSource({
        name: this.data.customName || undefined,
        source_type: this.data.sourceType,
        url: this.data.customUrl,
      });
      const data = res?.data || res;
      if (data && data.id) {
        const newSource = { ...data, _status: null, _checking: false };
        const customSources = [...this.data.customSources, newSource];
        const allSources = [...this.data.presetSources, ...customSources];
        this.setData({
          customSources,
          allSources,
          customUrl: '',
          customName: '',
          sourceType: 'rss',
          adding: false,
          activeTab: 'preset',
        });
        wx.showToast({ title: '添加成功', icon: 'success', duration: 1500 });
      }
    } catch (err) {
      console.error('addSource failed:', err);
      this.setData({ adding: false });
      const msg = err?.data?.message || err?.message || '添加失败';
      wx.showToast({ title: msg, icon: 'none', duration: 2000 });
    }
  },

  async onCheckSource(e) {
    const { item } = e.currentTarget.dataset;
    if (!item || item._checking) return;
    this._updateSource(item.id, { _checking: true, _status: null });
    try {
      const res = await newsService.checkSource(item.id);
      const d = res?.data || res;
      this._updateSource(item.id, { _checking: false, _status: d?.status || 'ok' });
      wx.showToast({ title: '检测成功', icon: 'success', duration: 1500 });
    } catch (err) {
      console.error('checkSource failed:', err);
      this._updateSource(item.id, { _checking: false, _status: 'error' });
      wx.showToast({ title: '检测失败', icon: 'none', duration: 1500 });
    }
  },

  async onToggleSource(e) {
    const { item } = e.currentTarget.dataset;
    if (!item) return;
    try {
      const res = await newsService.toggleSource(item.id);
      const d = res?.data || res;
      const newEnabled = d?.is_enabled !== undefined ? !!d.is_enabled : !item.is_enabled;
      this._updateSource(item.id, { is_enabled: newEnabled });
      wx.showToast({ title: newEnabled ? '打开成功' : '关闭成功', icon: 'success', duration: 1500 });
    } catch (err) {
      console.error('toggleSource failed:', err);
      wx.showToast({ title: '操作失败', icon: 'none', duration: 1500 });
    }
  },

  onDeleteSource(e) {
    const { item } = e.currentTarget.dataset;
    if (!item) return;
    wx.showModal({
      title: '删除源',
      content: '删除 "' + item.name + '" 源',
      success: async (res) => {
        if (res.confirm) {
          await this._doDeleteSource(item);
        }
      }
    });
  },

  async _doDeleteSource(item) {
    try {
      await newsService.deleteSource(item.id);
      const customSources = this.data.customSources.filter(s => s.id !== item.id);
      const allSources = [...this.data.presetSources, ...customSources];
      this.setData({ customSources, allSources });
      wx.showToast({ title: '删除成功', icon: 'success', duration: 1500 });
    } catch (err) {
      console.error('deleteSource failed:', err);
      wx.showToast({ title: '删除失败', icon: 'none', duration: 1500 });
    }
  },

  _updateSource(id, updates) {
    const apply = arr => arr.map(s => s.id === id ? Object.assign({}, s, updates) : s);
    const presetSources = apply(this.data.presetSources);
    const customSources = apply(this.data.customSources);
    const allSources = [...presetSources, ...customSources];
    this.setData({ presetSources, customSources, allSources });
  },

  onBack() {
    wx.navigateBack();
  },
});
