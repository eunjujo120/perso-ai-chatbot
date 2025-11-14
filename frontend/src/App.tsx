// src/App.tsx
import ChatPage from "./pages/ChatPage";

function App() {
  return (
    <div className="min-h-screen flex flex-col bg-[#f4f3ff]">
      {/* 상단 퍼플 헤더 */}
      <header className="bg-[#7b5cff] text-white shadow-md">
        <div className="w-full max-w-5xl mx-auto px-4 py-3 flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-white/90 flex items-center justify-center text-sm font-bold text-[#7b5cff]">
            P
          </div>
          <span className="font-semibold text-base">Perso AI 챗봇</span>
        </div>
      </header>

      {/* 헤더 아래 영역 전체를 사용하면서, 중앙에 카드 하나 */}
      <main className="flex-1 flex items-center justify-center px-4 py-6">
        <ChatPage />
      </main>
    </div>
  );
}

export default App;
