/**
 * AI法律助手 - 用户服务
 */
const api = require('../utils/api');

module.exports = {
  getProfile() { return api.get('/user/profile'); },
  updateProfile(nickname, avatarUrl) {
    const data = {};
    if (nickname !== undefined) data.nickname = nickname;
    if (avatarUrl !== undefined) data.avatar_url = avatarUrl;
    return api.put('/user/profile', data);
  },
  updatePrivacy(saveHistory) {
    return api.put('/user/privacy', { privacy_save_history: saveHistory });
  }
};
