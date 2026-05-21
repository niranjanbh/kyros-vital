module.exports = function (api) {
  api.cache(true);
  return {
    presets: [require('expo/internal/babel-preset')],
    plugins: [
      // Must be last
      'react-native-reanimated/plugin',
    ],
  };
};
