FROM node:20-alpine

WORKDIR /app

COPY package.json /app/
RUN npm install

COPY . /app

EXPOSE 9000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "9000"]
