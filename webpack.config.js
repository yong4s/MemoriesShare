const path = require('path');

const HtmlWebpackPlugin = require('html-webpack-plugin');
const ReactRefreshWebpackPlugin = require('@pmmmwh/react-refresh-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const NodePolyfillPlugin = require('node-polyfill-webpack-plugin');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');

module.exports = (env, argv) => {
  const isDev = argv.mode === 'development';
  const localhostOutput = {
    path: path.resolve('./frontend/webpack_bundles/'),
    publicPath: '/',
    filename: '[name].js',
  };
  const productionOutput = {
    path: path.resolve('./frontend/webpack_bundles/'),
    publicPath: '/static/webpack_bundles/',
    filename: '[name].js',
    clean: true,
  };

  return {
    mode: isDev ? 'development' : 'production',
    devtool: 'source-map',
    stats: isDev ? 'errors-warnings' : 'normal',
    infrastructureLogging: {
      level: 'error',
    },
    devServer: {
      hot: true,
      historyApiFallback: {
        index: '/index.html',
        disableDotRule: true,
      },
      host: '0.0.0.0',
      port: 3000,
      allowedHosts: 'all',
      // Allow CORS requests from the Django dev server domain:
      headers: { 'Access-Control-Allow-Origin': '*' },
      proxy: [
        {
          context: ['/api', '/admin', '/swagger', '/redoc', '/accounts'],
          target: 'http://backend:8000',
          changeOrigin: true,
        },
      ],
      devMiddleware: {
        publicPath: '/',
        stats: 'errors-warnings',
      },
      client: {
        logging: 'warn',
        overlay: {
          errors: true,
          warnings: false,
        },
      },
    },
    context: __dirname,
    entry: ['./frontend/js/index.tsx'],
    output: isDev ? localhostOutput : productionOutput,
    module: {
      rules: [
        {
          test: /\.(js|mjs|jsx|ts|tsx)$/,
          use: {
            loader: 'swc-loader',
            options: {
              jsc: {
                parser: {
                  syntax: 'typescript',
                  tsx: true,
                },
                transform: {
                  react: {
                    runtime: 'automatic',
                    development: isDev,
                    refresh: isDev,
                  },
                },
              },
            },
          },
        },
        {
          test: /\.css$/,
          use: [
            isDev && 'style-loader',
            !isDev && MiniCssExtractPlugin.loader,
            { loader: 'css-loader', options: { importLoaders: 1 } },
            // Tailwind v4 uses @tailwindcss/postcss (condigured in the postcss.config.mjs file)
            'postcss-loader',
          ].filter(Boolean),
        },
        {
          test: /\.(svg)(\?v=\d+\.\d+\.\d+)?$/,
          type: 'asset',
        },
        {
          test: /\.(woff(2)?|eot|ttf|otf)(\?v=\d+\.\d+\.\d+)?$/,
          type: 'asset',
        },
        {
          test: /\.(png|jpg|jpeg|gif|webp)?$/,
          type: 'asset',
        },
      ],
    },
    plugins: [
      new HtmlWebpackPlugin({
        templateContent: () => `
          <!doctype html>
          <html lang="en">
            <head>
              <meta charset="utf-8" />
              <meta name="viewport" content="width=device-width, initial-scale=1" />
              <link rel="preconnect" href="https://fonts.googleapis.com">
              <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
              <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
              <title>Media Flow</title>
              <script>
                window.SENTRY_DSN = '';
                window.COMMIT_SHA = 'local-dev';
                window.Urls = {};
              </script>
            </head>
            <body>
              <div id="react-app"></div>
            </body>
          </html>
        `,
      }),
      !isDev && new MiniCssExtractPlugin({ filename: '[name].css' }),
      isDev && new ReactRefreshWebpackPlugin(),
      !isDev &&
        new BundleTracker({
          path: __dirname,
          filename: 'webpack-stats.json',
        }),
      new NodePolyfillPlugin(),
      new webpack.ProvidePlugin({ Buffer: ['buffer', 'Buffer'] }),
    ].filter(Boolean),
    resolve: {
      fullySpecified: false,
      modules: ['node_modules', path.resolve(__dirname, 'frontend/js/')],
      alias: { '@': path.resolve(__dirname, 'frontend') },
      extensions: ['.js', '.jsx', '.ts', '.tsx'],
    },
    optimization: {
      minimize: !isDev,
      splitChunks: {
        // include all types of chunks
        chunks: 'all',
      },
    },
    watchOptions: {
      ignored: [
        '**/node_modules/**',
        '**/.git/**',
        '**/frontend/webpack_bundles/**',
        '**/webpack-stats.json',
      ],
    },
  };
};
