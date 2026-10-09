import Calculator from './components/Calculator'

export default function App() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-4 bg-slate-100">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight sm:text-5xl">
          High-Precision Calculator
        </h1>
        <p className="mt-3 text-lg text-slate-600">
          PEMDAS Compliant Web Calculator via Spec-Driven Development
        </p>
      </div>
      <Calculator />
    </main>
  )
}
