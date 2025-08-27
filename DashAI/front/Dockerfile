FROM node:22-alpine

WORKDIR /app
COPY package.json yarn.lock .yarnrc.yml ./
COPY .yarn ./.yarn
RUN yarn install --immutable
COPY . .

# Start development server
CMD ["yarn", "start"]
