import { NextPage } from "next";

const HomePage: NextPage = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <main className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-gray-900 text-center mb-8">
          Swiss News Aggregator
        </h1>
        <p className="text-lg text-gray-600 text-center">
          Your source for Swiss news across all languages
        </p>
      </main>
    </div>
  );
};

export default HomePage;
