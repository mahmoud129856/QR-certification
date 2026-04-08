class CompetitionDashboard {
    constructor() {
        this.data = {};
        this.chart = null;
        this.init();
    }

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
        } catch (error) {
            console.error('Error fetching data:', error);
        }
    }

    sortTeams() {
        this.data.teams.sort((a, b) => b.score - a.score);
        this.data.teams.forEach((team, index) => {
            team.rank = index + 1;
        });
    }

    renderLeaderboard() {
        const container = document.getElementById('leaderboard');
        container.innerHTML = this.data.teams.map((team, index) => `
            <div class="leaderboard-item flex items-center p-6 rounded-2xl bg-black/30 border border-white/20 hover:bg-white/10 ${index === 0 ? 'rank-1 glow' : index === 1 ? 'rank-2' : index === 2 ? 'rank-3' : ''}">
                <div class="flex-shrink-0 w-12 h-12 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-2xl flex items-center justify-center font-bold text-xl shadow-2xl ${index === 0 ? 'text-black scale-110' : ''}">
                    #${team.rank}
                </div>
                <div class="ml-6 flex-1 min-w-0">
                    <h3 class="text-xl md:text-2xl font-bold truncate">${team.name}</h3>
                    <div class="flex items-center space-x-4 text-sm opacity-90 mt-1">
                        <span class="font-mono text-2xl">${team.score.toLocaleString()}</span>
                        <span class="px-3 py-1 bg-white/20 rounded-full text-xs">+${Math.floor(Math.random() * 10)}</span>
                    </div>
                </div>
                <div class="text-right ml-6">
                    <i class="fas fa-arrow-up text-green-400 text-2xl"></i>
                </div>
            </div>
        `).join('');
    }

    renderMVP() {
        const { name, team, score } = this.data.mvp;
        document.getElementById('mvp-card').innerHTML = `
            <div class="max-w-md mx-auto p-8 bg-black/30 rounded-3xl border-4 border-yellow-400/50 glow">
                <div class="w-24 h-24 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-full mx-auto mb-6 flex items-center justify-center text-3xl font-bold text-black shadow-2xl">
                    <i class="fas fa-star"></i>
                </div>
                <h3 class="text-2xl md:text-3xl font-bold mb-2">${name}</h3>
                <p class="text-lg opacity-90 mb-4">${team}</p>
                <div class="font-mono text-4xl font-bold text-yellow-400">${score} pts</div>
            </div>
        `;
    }

    renderTeamsOverview() {
        const container = document.getElementById('teams-grid');
        container.innerHTML = this.data.teams.map(team => `
            <div class="team-card bg-black/30 backdrop-blur-md rounded-3xl p-8 border border-white/20 hover:border-yellow-400/50">
                <h3 class="text-xl font-bold mb-4 truncate">${team.name}</h3>
                <div class="space-y-3 text-sm">
                    <div class="flex items-center">
                        <i class="fas fa-users text-blue-400 mr-3"></i>
                        <span>${team.members} members</span>
                    </div>
                    <div class="flex items-center">
                        <i class="fas fa-lightbulb text-yellow-400 mr-3"></i>
                        <span>${team.ideas} ideas</span>
                    </div>
                    <div class="flex items-center pt-4 border-t border-white/20">
                        <i class="fas fa-coins text-green-400 mr-3"></i>
                        <span class="font-mono text-2xl font-bold text-green-400">${team.score.toLocaleString()}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    renderNewsTicker() {
        const container = document.getElementById('news-ticker');
        const newsItems = this.data.news.slice(0, 8).map(item => `<span class="mx-8 font-medium">${item}</span>`).join('');
        container.querySelector('.animate-marquee').innerHTML = newsItems + newsItems; // Duplicate for seamless loop
    }

    renderChart() {
        const ctx = document.getElementById('scoreChart').getContext('2d');
        
        if (this.chart) {
            this.chart.destroy();
        }

        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: this.data.teams.map(team => team.name),
                datasets: [{
                    label: 'Score',
                    data: this.data.teams.map(team => team.score),
                    backgroundColor: [
                        'rgba(251, 191, 36, 0.8)',
                        'rgba(59, 130, 246, 0.8)',
                        'rgba(16, 185, 129, 0.8)',
                        'rgba(168, 85, 247, 0.8)',
                        'rgba(245, 158, 11, 0.8)',
                        'rgba(236, 72, 153, 0.8)'
                    ],
                    borderColor: [
                        'rgba(251, 191, 36, 1)',
                        'rgba(59, 130, 246, 1)',
                        'rgba(16, 185, 129, 1)',
                        'rgba(168, 85, 247, 1)',
                        'rgba(245, 158, 11, 1)',
                        'rgba(236, 72, 153, 1)'
                    ],
                    borderWidth: 2,
                    borderRadius: 12,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255,255,255,0.1)' },
                        ticks: { color: 'white' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { 
                            color: 'white',
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                },
                animation: {
                    duration: 2000,
                    easing: 'easeOutBounce'
                }
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
                
                document.getElementById('countdown').textContent = 
                    `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            } else {
                document.getElementById('countdown').textContent = 'COMPETITION ENDED!';
            }
        };

        updateCountdown();
        setInterval(updateCountdown, 1000);
    }

    async startAutoRefresh() {
        setInterval(async () => {
            await this.fetchData();
            this.renderAll();
        }, 10000); // Refresh every 10 seconds
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new CompetitionDashboard();
});