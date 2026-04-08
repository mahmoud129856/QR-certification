class CompetitionDashboard {
    constructor() { this.data = {}; this.chart = null; this.init(); }

    async init() {
        await this.fetchData();
        this.renderAll();
        this.startCountdown();
        this.startAutoRefresh();
    }

    async fetchData() {
        try {
            const response = await fetch('/api/data');
            this.data = await response.json();
            this.sortTeams();
        } catch (error) { console.error('Error:', error); }
    }

    sortTeams() {
        this.data.teams.sort((a, b) => b.score - a.score);
        this.data.teams.forEach((team, index) => team.rank = index + 1);
    }

    renderLeaderboard() {
        document.getElementById('leaderboard').innerHTML = this.data.teams.slice(0, 6).map((team, index) => `
            <div class="leaderboard-item group flex items-center p-4 rounded-xl bg-black/50 border border-white/30 hover:bg-white/10 transition-all duration-200 custom-scrollbar">
                <div class="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center font-bold text-sm shadow-lg mr-3
                    ${index === 0 ? 'bg-gradient-to-r from-yellow-400 to-orange-500 text-black scale-110' : 
                      index === 1 ? 'bg-gradient-to-r from-gray-500 to-gray-600 text-white' : 
                      index === 2 ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white' : 'bg-white/20 text-white'}">
                    #${team.rank}
                </div>
                <div class="flex-1 min-w-0">
                    <h3 class="font-bold text-base truncate">${team.name}</h3>
                    <div class="flex items-center justify-between mt-1">
                        <span class="font-mono text-lg font-bold text-yellow-400">${team.score}</span>
                        <span class="px-2 py-0.5 bg-green-500/30 text-green-300 text-xs rounded-full font-medium">+${Math.floor(Math.random() * 5)}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    renderMVP() {
        const { name, team, score } = this.data.mvp;
        document.getElementById('mvp-card').innerHTML = `
            <div class="p-4 rounded-xl bg-black/40 border-2 border-yellow-400/50">
                <div class="w-16 h-16 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-full mx-auto mb-3 flex items-center justify-center shadow-xl">
                    <i class="fas fa-star text-black text-xl"></i>
                </div>
                <h3 class="font-bold text-lg mb-1 leading-tight">${name}</h3>
                <p class="text-sm text-indigo-300 mb-3 truncate">${team}</p>
                <div class="font-mono text-2xl font-bold bg-gradient-to-r from-yellow-400 to-orange-500 bg-clip-text text-transparent">${score} نقطة</div>
            </div>
        `;
    }

    renderTeamsOverview() {
        document.getElementById('teams-grid').innerHTML = this.data.teams.map(team => `
            <div class="p-4 rounded-xl bg-black/40 border border-white/20 hover:border-yellow-400/50 transition-all duration-200">
                <div class="flex items-start justify-between mb-2">
                    <h3 class="font-bold text-base flex-1 pr-2 truncate">${team.name}</h3>
                    <span class="font-mono text-lg font-bold text-yellow-400">${team.score}</span>
                </div>
                <div class="space-y-2 text-xs text-indigo-300 -mx-1">
                    <div class="flex items-center px-1"><i class="fas fa-users text-blue-400 mr-2 w-4"></i>${team.members} عضو</div>
                    <div class="flex items-center px-1"><i class="fas fa-lightbulb text-yellow-400 mr-2 w-4"></i>${team.ideas} فكرة</div>
                </div>
            </div>
        `).join('');
    }

    renderNewsTicker() {
        const container = document.getElementById('news-marquee');
        const newsItems = this.data.news.slice(0, 6).map(item => 
            `<span class="mx-4 px-3 py-1 bg-black/60 rounded-lg font-medium text-sm text-right">${item}</span>`
        ).join('');
        container.innerHTML = newsItems.repeat(25); // Seamless RTL
    }

    renderChart() {
        const ctx = document.getElementById('scoreChart').getContext('2d');
        if (this.chart) this.chart.destroy();
        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: this.data.teams.map(team => team.name.length > 12 ? team.name.substring(0,12) + '...' : team.name),
                datasets: [{
                    data: this.data.teams.map(team => team.score),
                    backgroundColor: 'rgba(251, 191, 36, 0.8)',
                    borderColor: 'rgba(251, 191, 36, 1)',
                    borderWidth: 2,
                    borderRadius: 8,
                    barThickness: 28
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.08)' }, ticks: { color: 'white', font: { size: 11 }, stepSize: 20 } },
                    x: { grid: { display: false }, ticks: { color: 'white', font: { size: 11 }, maxRotation: 0 } }
                },
                animation: { duration: 1500, easing: 'easeOutQuart' }
            }
        });
    }

    renderAll() {
        this.renderLeaderboard();
        this.renderMVP();
        this.renderTeamsOverview();
        this.renderNewsTicker();
        this.renderChart();
    }

    startCountdown() {
        const endTime = new Date(this.data.end_time);
        const updateCountdown = () => {
            const now = new Date();
            const diff = endTime - now;
            if (diff > 0) {
                const hours = Math.floor(diff / (1000 * 60 * 60));
                const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((diff % (1000 * 60)) / 1000);
                document.getElementById('countdown').textContent = `${hours}س ${minutes}د ${seconds}ث`;
            } else {
                const el = document.getElementById('countdown');
                el.textContent = 'انتهت';
                el.className = 'text-sm font-mono bg-red-500/30 px-3 py-1.5 rounded-full border border-red-500/50 font-bold min-w-[80px] text-center';
            }
        };
        updateCountdown();
        setInterval(updateCountdown, 1000);
    }

    async startAutoRefresh() {
        setInterval(async () => {
            await this.fetchData();
            this.renderAll();
        }, 15000);
    }
}

document.addEventListener('DOMContentLoaded', () => new CompetitionDashboard());